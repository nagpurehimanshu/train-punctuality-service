from __future__ import annotations

"""Prediction engine — predicts delays at each station for a train.

Uses tiered approach:
1. Weighted average (primary for MVP — works with any amount of data)
2. Prophet/sklearn added in later phases when we have 60+ data points

Confidence is based on data sufficiency and variance.
"""


import math
from src.db.repositories.query_repo import get_avg_delay_by_station
from src.db.database import get_connection
from config.constants import MIN_POINTS_AVERAGE, MAX_CONFIDENCE_LOW_DATA


def predict_train(train_number: str, days: int = 90) -> list[dict]:
    """Predict delay at each station based on historical averages.

    Returns list of dicts with station_code, predicted_delay_min, confidence_pct, etc.
    """
    stats = get_avg_delay_by_station(train_number, days)
    if not stats:
        return []

    # Get schedule for station names
    conn = get_connection()
    schedule = {
        r[0]: {"station_name": r[1], "scheduled_arrival": r[2], "scheduled_departure": r[3]}
        for r in conn.execute(
            """SELECT s.station_code, s.station_name, ts.scheduled_arrival, ts.scheduled_departure
               FROM train_schedule ts
               JOIN stations s ON ts.station_code = s.station_code
               WHERE ts.train_number=? ORDER BY ts.sequence""",
            (train_number,),
        ).fetchall()
    }

    predictions = []
    for s in stats:
        stn = s["station_code"]
        avg_delay = s["avg_delay"]
        data_points = s["data_points"]
        min_d = s["min_delay"]
        max_d = s["max_delay"]

        confidence = _compute_confidence(data_points, min_d, max_d, avg_delay)
        sched = schedule.get(stn, {})

        predicted_arrival = _add_minutes(sched.get("scheduled_arrival"), avg_delay)

        predictions.append({
            "station_code": stn,
            "station_name": sched.get("station_name", stn),
            "sequence": s["sequence"],
            "scheduled_arrival": sched.get("scheduled_arrival"),
            "predicted_arrival": predicted_arrival,
            "predicted_delay_min": round(avg_delay, 1),
            "confidence_pct": confidence,
            "delay_range": {"min": min_d, "max": max_d},
            "data_points_used": data_points,
            "prediction_model": "weighted_average_v1",
        })

    return predictions


def _compute_confidence(data_points: int, min_delay: int, max_delay: int, avg_delay: float) -> float:
    """Confidence based on data sufficiency and variance."""
    if data_points < MIN_POINTS_AVERAGE:
        return min(MAX_CONFIDENCE_LOW_DATA, data_points * 4.0)

    # Base confidence from data volume (60+ points = 90% base)
    data_factor = min(1.0, data_points / 60)

    # Variance penalty — wide range = less confident
    spread = abs(max_delay - min_delay)
    variance_factor = max(0.5, 1.0 - (spread / 200))

    confidence = 90 * data_factor * variance_factor
    return round(min(99.0, max(5.0, confidence)), 1)


def _add_minutes(time_str: str | None, minutes: float) -> str | None:
    if not time_str:
        return None
    h, m = map(int, time_str.split(":"))
    total = h * 60 + m + round(minutes)
    total = total % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def compute_reliability_score(train_number: str, days: int = 90) -> dict | None:
    """Compute 0-100 reliability score for a train."""
    from src.db.repositories.query_repo import get_reliability_data, get_cancellation_rate, get_worst_stations

    data = get_reliability_data(train_number, days)
    if not data:
        return None

    cancel_rate = get_cancellation_rate(train_number, days)
    worst = get_worst_stations(train_number, days)

    # Score: 100 = perfect, penalize for delays and cancellations
    score = 100.0
    score -= min(30, data["avg_delay_min"] * 0.8)  # avg delay penalty
    score -= data["late_30_pct"] * 0.3  # late >30min penalty
    score -= cancel_rate * 0.5  # cancellation penalty
    score = round(max(0, min(100, score)), 0)

    return {
        "reliability_score": score,
        "cancellation_pct": cancel_rate,
        "worst_stations": worst,
        **data,
    }
