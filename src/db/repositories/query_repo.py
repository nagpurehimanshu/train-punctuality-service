from __future__ import annotations

"""Query repositories for API endpoints."""

from src.db.database import get_connection


def _rows_to_dicts(cursor_result, columns: list[str]) -> list[dict]:
    """Convert libsql rows to dicts since libsql doesn't support dict(row)."""

    return [dict(zip(columns, row)) for row in cursor_result]


def get_train_history(train_number: str, station_code: str, from_date: str, to_date: str) -> list[dict]:
    conn = get_connection()
    cols = ["run_date", "scheduled_arrival", "actual_arrival", "delay_arrival_min",
            "scheduled_departure", "actual_departure", "delay_departure_min", "platform_number"]
    rows = conn.execute(
        f"""SELECT {', '.join(cols)}
           FROM daily_stop_times
           WHERE train_number=? AND station_code=? AND run_date BETWEEN ? AND ?
           ORDER BY run_date""",
        (train_number, station_code, from_date, to_date),
    ).fetchall()
    return _rows_to_dicts(rows, cols)


def get_train_stops_for_date(train_number: str, run_date: str) -> list[dict]:
    conn = get_connection()
    cols = ["station_code", "station_name", "sequence",
            "scheduled_arrival", "actual_arrival", "delay_arrival_min",
            "scheduled_departure", "actual_departure", "delay_departure_min",
            "platform_number"]
    rows = conn.execute(
        """SELECT dst.station_code, s.station_name, dst.sequence,
                  dst.scheduled_arrival, dst.actual_arrival, dst.delay_arrival_min,
                  dst.scheduled_departure, dst.actual_departure, dst.delay_departure_min,
                  dst.platform_number
           FROM daily_stop_times dst
           LEFT JOIN stations s ON dst.station_code = s.station_code
           WHERE dst.train_number=? AND dst.run_date=?
           ORDER BY dst.sequence""",
        (train_number, run_date),
    ).fetchall()
    return _rows_to_dicts(rows, cols)


def get_reliability_data(train_number: str, days: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT COUNT(*) as total_runs,
                  AVG(delay_arrival_min) as avg_delay,
                  COUNT(CASE WHEN ABS(COALESCE(delay_arrival_min,0)) <= 5 THEN 1 END) as on_time_count,
                  COUNT(CASE WHEN delay_arrival_min > 15 THEN 1 END) as late_15_count,
                  COUNT(CASE WHEN delay_arrival_min > 30 THEN 1 END) as late_30_count,
                  COUNT(CASE WHEN delay_arrival_min > 60 THEN 1 END) as late_60_count
           FROM daily_stop_times
           WHERE train_number=?
             AND run_date >= date('now', ?)
             AND sequence = (SELECT MAX(sequence) FROM daily_stop_times d2 WHERE d2.train_number=daily_stop_times.train_number AND d2.run_date=daily_stop_times.run_date)""",
        (train_number, f"-{days} days"),
    ).fetchone()
    if not row or row[0] == 0:
        return None
    total = row[0]
    return {
        "total_runs": total,
        "avg_delay_min": round(row[1] or 0, 1),
        "on_time_pct": round(row[2] / total * 100, 1),
        "late_15_pct": round(row[3] / total * 100, 1),
        "late_30_pct": round(row[4] / total * 100, 1),
        "late_60_pct": round(row[5] / total * 100, 1),
    }


def get_cancellation_rate(train_number: str, days: int) -> float:
    conn = get_connection()
    row = conn.execute(
        """SELECT COUNT(*) as total,
                  COUNT(CASE WHEN run_status='CANCELLED' THEN 1 END) as cancelled
           FROM daily_runs
           WHERE train_number=? AND run_date >= date('now', ?)""",
        (train_number, f"-{days} days"),
    ).fetchone()
    if not row or row[0] == 0:
        return 0.0
    return round(row[1] / row[0] * 100, 1)


def get_worst_stations(train_number: str, days: int, limit: int = 3) -> list[dict]:
    conn = get_connection()
    cols = ["station_code", "station_name", "avg_delay"]
    rows = conn.execute(
        """SELECT dst.station_code, s.station_name, AVG(dst.delay_arrival_min) as avg_delay
           FROM daily_stop_times dst
           LEFT JOIN stations s ON dst.station_code = s.station_code
           WHERE dst.train_number=? AND dst.run_date >= date('now', ?)
             AND dst.delay_arrival_min IS NOT NULL
           GROUP BY dst.station_code
           ORDER BY avg_delay DESC
           LIMIT ?""",
        (train_number, f"-{days} days", limit),
    ).fetchall()
    return _rows_to_dicts(rows, cols)


def get_station_board(station_code: str, run_date: str) -> list[dict]:
    conn = get_connection()
    cols = ["train_number", "train_name", "origin_code", "destination_code",
            "scheduled_arrival", "actual_arrival", "delay_arrival_min",
            "scheduled_departure", "actual_departure", "delay_departure_min",
            "platform_number"]
    rows = conn.execute(
        """SELECT dst.train_number, t.train_name, t.origin_code, t.destination_code,
                  dst.scheduled_arrival, dst.actual_arrival, dst.delay_arrival_min,
                  dst.scheduled_departure, dst.actual_departure, dst.delay_departure_min,
                  dst.platform_number
           FROM daily_stop_times dst
           LEFT JOIN trains t ON dst.train_number = t.train_number
           WHERE dst.station_code=? AND dst.run_date=?
           ORDER BY COALESCE(dst.scheduled_arrival, dst.scheduled_departure)""",
        (station_code, run_date),
    ).fetchall()
    return _rows_to_dicts(rows, cols)


def get_avg_delay_by_station(train_number: str, days: int) -> list[dict]:
    conn = get_connection()
    cols = ["station_code", "sequence", "avg_delay", "data_points", "min_delay", "max_delay"]
    rows = conn.execute(
        """SELECT station_code, sequence,
                  AVG(delay_arrival_min) as avg_delay,
                  COUNT(*) as data_points,
                  MIN(delay_arrival_min) as min_delay,
                  MAX(delay_arrival_min) as max_delay
           FROM daily_stop_times
           WHERE train_number=? AND run_date >= date('now', ?)
             AND delay_arrival_min IS NOT NULL
           GROUP BY station_code, sequence
           ORDER BY sequence""",
        (train_number, f"-{days} days"),
    ).fetchall()
    return _rows_to_dicts(rows, cols)
