"""Station API endpoint — UC-9: Station live board."""

from fastapi import APIRouter, HTTPException, Query
from src.db.repositories.query_repo import get_station_board
from src.utils.time_utils import today_ist

router = APIRouter()


@router.get("/stations/{station_code}/board")
def station_board(station_code: str, date: str = Query(default=None)):
    """UC-9: All trains at a station with actual/predicted times."""
    run_date = date or today_ist()
    data = get_station_board(station_code.upper(), run_date)
    if not data:
        raise HTTPException(404, f"No data for station {station_code} on {run_date}")

    arrivals = [d for d in data if d.get("scheduled_arrival")]
    departures = [d for d in data if d.get("scheduled_departure")]

    return {
        "station_code": station_code.upper(),
        "date": run_date,
        "arrivals": arrivals,
        "departures": departures,
    }
