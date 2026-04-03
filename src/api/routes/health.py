from fastapi import APIRouter
from src.db.database import get_connection
from src.utils.time_utils import now_ist

router = APIRouter()


@router.get("/health")
def health_check():
    conn = get_connection()
    train_count = conn.execute("SELECT COUNT(*) FROM trains").fetchone()[0]
    station_count = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    last_log = conn.execute(
        "SELECT status, completed_at FROM collection_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    return {
        "status": "ok",
        "timestamp": now_ist().isoformat(),
        "data": {
            "trains_tracked": train_count,
            "stations_tracked": station_count,
            "last_collection": dict(last_log) if last_log else None,
        },
    }
