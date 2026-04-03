"""History API endpoint — UC-2."""

from fastapi import APIRouter, HTTPException, Query
from src.db.repositories.query_repo import get_train_history
from src.utils.time_utils import today_ist

router = APIRouter()


@router.get("/trains/{train_number}/stations/{station_code}/history")
def history(
    train_number: str,
    station_code: str,
    from_date: str = Query(default=None, alias="from"),
    to_date: str = Query(default=None, alias="to"),
):
    """UC-2: Historical actual times at a station over a period."""
    to_d = to_date or today_ist()
    from_d = from_date or _subtract_days(to_d, 30)

    data = get_train_history(train_number, station_code.upper(), from_d, to_d)
    if not data:
        raise HTTPException(404, f"No history for {train_number} at {station_code}")

    delays = [d["delay_arrival_min"] for d in data if d["delay_arrival_min"] is not None]
    summary = {}
    if delays:
        summary = {
            "total_runs": len(data),
            "avg_delay_min": round(sum(delays) / len(delays), 1),
            "on_time_count": sum(1 for d in delays if abs(d) <= 5),
        }

    return {
        "train_number": train_number,
        "station_code": station_code.upper(),
        "from": from_d,
        "to": to_d,
        "data_points": data,
        "summary": summary,
    }


def _subtract_days(date_str: str, days: int) -> str:
    from datetime import datetime, timedelta
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return (d - timedelta(days=days)).strftime("%Y-%m-%d")
