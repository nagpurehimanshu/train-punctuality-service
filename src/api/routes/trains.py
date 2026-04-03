"""Train API endpoints — UC-1 (predict), UC-3 (reliability)."""

from fastapi import APIRouter, HTTPException, Query
from src.prediction.predictor import predict_train, compute_reliability_score
from src.db.repositories.query_repo import get_train_stops_for_date
from src.utils.time_utils import today_ist

router = APIRouter()


@router.get("/trains/{train_number}/predict")
def predict(train_number: str, date: str = Query(default=None)):
    """UC-1: Predicted arrival/departure at all stations with confidence %."""
    predictions = predict_train(train_number)
    if not predictions:
        # Fallback: return latest actual data if no prediction model data
        run_date = date or today_ist()
        stops = get_train_stops_for_date(train_number, run_date)
        if not stops:
            raise HTTPException(404, f"No data for train {train_number}")
        return {"train_number": train_number, "date": run_date, "source": "historical", "route": stops}

    return {
        "train_number": train_number,
        "date": date or today_ist(),
        "prediction_model": "weighted_average_v1",
        "route": predictions,
    }


@router.get("/trains/{train_number}/reliability")
def reliability(train_number: str, period: str = Query(default="90d")):
    """UC-3: Train reliability score 0-100 with breakdown."""
    days = _parse_period(period)
    result = compute_reliability_score(train_number, days)
    if not result:
        raise HTTPException(404, f"No data for train {train_number}")
    return {"train_number": train_number, "period": period, **result}


def _parse_period(period: str) -> int:
    period = period.lower().strip()
    if period.endswith("d"):
        return int(period[:-1])
    if period.endswith("m"):
        return int(period[:-1]) * 30
    if period.endswith("y"):
        return int(period[:-1]) * 365
    return 90
