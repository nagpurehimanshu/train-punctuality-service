"""Repository for storing and querying daily train run data."""

from datetime import date
from src.db.database import get_connection
from src.scraper.ntes_client import TrainRun, StopTime
from src.utils.time_utils import now_ist
from src.utils.season_utils import is_fog_season, is_monsoon_season, get_holiday, get_festival_period


def upsert_daily_run(run: TrainRun) -> int:
    """Insert or update a daily run and its stop times. Returns daily_run id."""
    conn = get_connection()
    run_date = _parse_start_date(run.start_date)
    d = date.fromisoformat(run_date)

    conn.execute(
        """INSERT INTO daily_runs
           (train_number, run_date, run_status, data_completeness,
            collection_attempts, last_collected_at,
            is_fog_season, is_monsoon_season, is_festival_period, festival_name,
            is_public_holiday, day_of_week)
           VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(train_number, run_date) DO UPDATE SET
            run_status=excluded.run_status,
            data_completeness=excluded.data_completeness,
            collection_attempts=collection_attempts+1,
            last_collected_at=excluded.last_collected_at""",
        (
            run.train_number, run_date, run.status,
            _completeness(run.stops),
            now_ist().isoformat(),
            int(is_fog_season(d)), int(is_monsoon_season(d)),
            int(bool(get_festival_period(d))), get_festival_period(d),
            int(bool(get_holiday(d))), d.weekday(),
        ),
    )

    row = conn.execute(
        "SELECT id FROM daily_runs WHERE train_number=? AND run_date=?",
        (run.train_number, run_date),
    ).fetchone()
    run_id = row[0]

    # Ensure stations exist (auto-create from scraped data)
    for stop in run.stops:
        conn.execute(
            "INSERT OR IGNORE INTO stations (station_code, station_name, updated_at) VALUES (?, ?, ?)",
            (stop.station_code, stop.station_name, now_ist().isoformat()),
        )

    for stop in run.stops:
        conn.execute(
            """INSERT INTO daily_stop_times
               (daily_run_id, train_number, run_date, station_code, sequence,
                scheduled_arrival, scheduled_departure,
                actual_arrival, actual_departure,
                delay_arrival_min, delay_departure_min,
                platform_number, collected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(train_number, run_date, station_code, sequence) DO UPDATE SET
                actual_arrival=excluded.actual_arrival,
                actual_departure=excluded.actual_departure,
                delay_arrival_min=excluded.delay_arrival_min,
                delay_departure_min=excluded.delay_departure_min,
                platform_number=excluded.platform_number,
                collected_at=excluded.collected_at""",
            (
                run_id, run.train_number, run_date, stop.station_code, stop.sequence,
                stop.scheduled_arrival, stop.scheduled_departure,
                stop.actual_arrival, stop.actual_departure,
                stop.delay_arrival_min, stop.delay_departure_min,
                stop.platform, now_ist().isoformat(),
            ),
        )

    conn.commit()
    return run_id


def _completeness(stops: list[StopTime]) -> float:
    if not stops:
        return 0.0
    has_actual = sum(1 for s in stops if s.actual_arrival or s.actual_departure)
    return has_actual / len(stops)


def _parse_start_date(start_date: str) -> str:
    """Convert '01-Apr-2026' to '2026-04-01'."""
    from datetime import datetime
    if not start_date:
        return now_ist().strftime("%Y-%m-%d")
    try:
        return datetime.strptime(start_date, "%d-%b-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return start_date
