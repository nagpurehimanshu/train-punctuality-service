"""Tests for daily_run_repo — upsert logic, completeness, date parsing."""

import pytest
import libsql_experimental as libsql
from pathlib import Path
from src.db.repositories.daily_run_repo import upsert_daily_run, _completeness, _parse_start_date
from src.scraper.ntes_client import TrainRun, StopTime

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Use a fresh temp DB for each test."""
    db_path = str(tmp_path / "test.db")

    def patched_get():
        conn = libsql.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # Patch in both modules
    import src.db.database as db_mod
    import src.db.repositories.daily_run_repo as repo_mod
    monkeypatch.setattr(db_mod, "get_connection", patched_get)
    monkeypatch.setattr(repo_mod, "get_connection", patched_get)

    # Init schema
    conn = patched_get()
    for stmt in _SCHEMA_PATH.read_text().split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
    yield


def _make_run(stops_count=3, status="COMPLETED", date="01-Apr-2026") -> TrainRun:
    stops = []
    for i in range(stops_count):
        stops.append(StopTime(
            station_code=f"ST{i}",
            station_name=f"Station {i}",
            sequence=i + 1,
            scheduled_arrival=f"10:{i:02d}" if i > 0 else None,
            actual_arrival=f"10:{i + 5:02d}" if i > 0 else None,
            delay_arrival_min=5 if i > 0 else None,
            scheduled_departure=f"10:{i + 1:02d}" if i < stops_count - 1 else None,
            actual_departure=f"10:{i + 6:02d}" if i < stops_count - 1 else None,
            platform=i + 1,
            distance_km=i * 100,
        ))
    return TrainRun(
        train_number="12301",
        train_name="Test Express",
        start_date=date,
        status=status,
        stops=stops,
    )


class TestUpsertDailyRun:
    def test_insert_new_run(self):
        run = _make_run()
        run_id = upsert_daily_run(run)
        assert run_id == 1

        from src.db.database import get_connection
        conn = get_connection()
        row = conn.execute("SELECT train_number, run_date, run_status FROM daily_runs WHERE id=?", (run_id,)).fetchone()
        assert row[0] == "12301"
        assert row[1] == "2026-04-01"
        assert row[2] == "COMPLETED"

    def test_stop_times_stored(self):
        run = _make_run(stops_count=5)
        upsert_daily_run(run)

        from src.db.database import get_connection
        count = get_connection().execute("SELECT COUNT(*) FROM daily_stop_times").fetchone()[0]
        assert count == 5

    def test_upsert_updates_existing(self):
        run1 = _make_run()
        id1 = upsert_daily_run(run1)

        run2 = _make_run()
        run2.stops[1].actual_arrival = "10:30"
        id2 = upsert_daily_run(run2)

        assert id1 == id2

        from src.db.database import get_connection
        conn = get_connection()
        assert conn.execute("SELECT COUNT(*) FROM daily_runs").fetchone()[0] == 1
        assert conn.execute("SELECT collection_attempts FROM daily_runs WHERE id=?", (id1,)).fetchone()[0] == 2

    def test_stop_times_upsert(self):
        run = _make_run(stops_count=3)
        upsert_daily_run(run)

        run.stops[1].actual_arrival = "11:00"
        run.stops[1].delay_arrival_min = 55
        upsert_daily_run(run)

        from src.db.database import get_connection
        conn = get_connection()
        assert conn.execute("SELECT COUNT(*) FROM daily_stop_times").fetchone()[0] == 3
        updated = conn.execute(
            "SELECT actual_arrival, delay_arrival_min FROM daily_stop_times WHERE station_code='ST1'"
        ).fetchone()
        assert updated[0] == "11:00"
        assert updated[1] == 55

    def test_stations_auto_created(self):
        run = _make_run(stops_count=3)
        upsert_daily_run(run)

        from src.db.database import get_connection
        assert get_connection().execute("SELECT COUNT(*) FROM stations").fetchone()[0] == 3

    def test_seasonal_flags_fog(self):
        run = _make_run(date="15-Jan-2026")
        upsert_daily_run(run)

        from src.db.database import get_connection
        row = get_connection().execute("SELECT is_fog_season FROM daily_runs").fetchone()
        assert row[0] == 1

    def test_seasonal_flags_no_fog_in_summer(self):
        run = _make_run(date="15-May-2026")
        upsert_daily_run(run)

        from src.db.database import get_connection
        row = get_connection().execute("SELECT is_fog_season FROM daily_runs").fetchone()
        assert row[0] == 0

    def test_cancelled_run(self):
        run = TrainRun(train_number="12301", start_date="01-Apr-2026", status="CANCELLED", stops=[])
        upsert_daily_run(run)

        from src.db.database import get_connection
        row = get_connection().execute("SELECT run_status, data_completeness FROM daily_runs").fetchone()
        assert row[0] == "CANCELLED"
        assert row[1] == 0.0

    def test_different_dates_separate_runs(self):
        upsert_daily_run(_make_run(date="01-Apr-2026"))
        upsert_daily_run(_make_run(date="02-Apr-2026"))

        from src.db.database import get_connection
        assert get_connection().execute("SELECT COUNT(*) FROM daily_runs").fetchone()[0] == 2


class TestCompleteness:
    def test_all_have_actual(self):
        stops = [
            StopTime("A", "A", 1, actual_departure="10:00"),
            StopTime("B", "B", 2, actual_arrival="11:00", actual_departure="11:05"),
            StopTime("C", "C", 3, actual_arrival="12:00"),
        ]
        assert _completeness(stops) == 1.0

    def test_none_have_actual(self):
        stops = [StopTime("A", "A", 1), StopTime("B", "B", 2)]
        assert _completeness(stops) == 0.0

    def test_partial(self):
        stops = [
            StopTime("A", "A", 1, actual_departure="10:00"),
            StopTime("B", "B", 2),
            StopTime("C", "C", 3),
        ]
        assert abs(_completeness(stops) - 1 / 3) < 0.01

    def test_empty(self):
        assert _completeness([]) == 0.0


class TestParseDateFormat:
    def test_standard_format(self):
        assert _parse_start_date("01-Apr-2026") == "2026-04-01"

    def test_december(self):
        assert _parse_start_date("25-Dec-2026") == "2026-12-25"

    def test_already_iso(self):
        assert _parse_start_date("2026-04-01") == "2026-04-01"

    def test_empty_returns_today(self):
        result = _parse_start_date("")
        assert len(result) == 10
