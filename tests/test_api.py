"""Integration tests for API endpoints using TestClient."""

import pytest
import libsql_experimental as libsql
from pathlib import Path
from fastapi.testclient import TestClient

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")

    def patched_get():
        conn = libsql.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # Patch everywhere
    import src.db.database as db_mod
    import src.db.repositories.daily_run_repo as repo_mod
    import src.db.repositories.query_repo as query_mod
    import src.prediction.predictor as pred_mod
    for mod in [db_mod, repo_mod, query_mod, pred_mod]:
        monkeypatch.setattr(mod, "get_connection", patched_get)

    # Init schema
    conn = patched_get()
    for stmt in _SCHEMA_PATH.read_text().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()

    from src.main import app
    return TestClient(app)


def _seed_data(monkeypatch_get):
    """Insert sample train data for testing."""
    conn = monkeypatch_get()
    conn.execute("INSERT INTO stations (station_code, station_name, updated_at) VALUES ('HWH', 'Howrah Jn', '2026-04-01')")
    conn.execute("INSERT INTO stations (station_code, station_name, updated_at) VALUES ('CNB', 'Kanpur Central', '2026-04-01')")
    conn.execute("INSERT INTO stations (station_code, station_name, updated_at) VALUES ('NDLS', 'New Delhi', '2026-04-01')")
    conn.execute("INSERT INTO trains (train_number, train_name, origin_code, destination_code, run_days, updated_at) VALUES ('12301', 'Rajdhani', 'HWH', 'NDLS', '[\"Daily\"]', '2026-04-01')")
    conn.execute("INSERT INTO daily_runs (train_number, run_date, run_status, day_of_week) VALUES ('12301', '2026-04-01', 'COMPLETED', 2)")
    conn.execute("""INSERT INTO daily_stop_times
        (daily_run_id, train_number, run_date, station_code, sequence,
         scheduled_arrival, actual_arrival, delay_arrival_min,
         scheduled_departure, actual_departure, collected_at)
        VALUES (1, '12301', '2026-04-01', 'HWH', 1, NULL, NULL, NULL, '16:50', '16:50', '2026-04-01')""")
    conn.execute("""INSERT INTO daily_stop_times
        (daily_run_id, train_number, run_date, station_code, sequence,
         scheduled_arrival, actual_arrival, delay_arrival_min,
         scheduled_departure, actual_departure, collected_at)
        VALUES (1, '12301', '2026-04-01', 'CNB', 2, '04:45', '04:58', 13, '04:50', '05:03', '2026-04-01')""")
    conn.execute("""INSERT INTO daily_stop_times
        (daily_run_id, train_number, run_date, station_code, sequence,
         scheduled_arrival, actual_arrival, delay_arrival_min,
         scheduled_departure, actual_departure, collected_at)
        VALUES (1, '12301', '2026-04-01', 'NDLS', 3, '10:05', '10:05', 0, NULL, NULL, '2026-04-01')""")
    conn.commit()


class TestHealthEndpoint:
    def test_health_ok(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestTrainEndpoints:
    def test_predict_no_data_404(self, client):
        r = client.get("/api/v1/trains/99999/predict")
        assert r.status_code == 404

    def test_predict_with_data(self, client, monkeypatch):
        import src.db.repositories.query_repo as query_mod
        _seed_data(query_mod.get_connection)
        r = client.get("/api/v1/trains/12301/predict?date=2026-04-01")
        assert r.status_code == 200
        body = r.json()
        assert body["train_number"] == "12301"
        assert len(body["route"]) > 0

    def test_reliability_no_data_404(self, client):
        r = client.get("/api/v1/trains/99999/reliability")
        assert r.status_code == 404

    def test_reliability_period_parsing(self, client):
        # Just verify it doesn't crash with different period formats
        for period in ["30d", "3m", "1y"]:
            r = client.get(f"/api/v1/trains/99999/reliability?period={period}")
            assert r.status_code == 404  # no data, but didn't crash


class TestHistoryEndpoint:
    def test_history_no_data_404(self, client):
        r = client.get("/api/v1/trains/99999/stations/CNB/history")
        assert r.status_code == 404

    def test_history_with_data(self, client, monkeypatch):
        import src.db.repositories.query_repo as query_mod
        _seed_data(query_mod.get_connection)
        r = client.get("/api/v1/trains/12301/stations/CNB/history?from=2026-03-01&to=2026-04-30")
        assert r.status_code == 200
        body = r.json()
        assert body["station_code"] == "CNB"
        assert len(body["data_points"]) == 1
        assert body["data_points"][0]["delay_arrival_min"] == 13

    def test_history_case_insensitive_station(self, client, monkeypatch):
        import src.db.repositories.query_repo as query_mod
        _seed_data(query_mod.get_connection)
        r = client.get("/api/v1/trains/12301/stations/cnb/history?from=2026-03-01&to=2026-04-30")
        assert r.status_code == 200


class TestStationBoardEndpoint:
    def test_board_no_data_404(self, client):
        r = client.get("/api/v1/stations/XXXX/board?date=2026-04-01")
        assert r.status_code == 404

    def test_board_with_data(self, client, monkeypatch):
        import src.db.repositories.query_repo as query_mod
        _seed_data(query_mod.get_connection)
        r = client.get("/api/v1/stations/CNB/board?date=2026-04-01")
        assert r.status_code == 200
        body = r.json()
        assert body["station_code"] == "CNB"
        assert len(body["arrivals"]) > 0
