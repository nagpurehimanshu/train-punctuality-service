from fastapi import APIRouter
from src.db.database import get_connection
from src.utils.time_utils import now_ist

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        conn = get_connection()
        train_count = conn.execute("SELECT COUNT(*) FROM trains").fetchone()[0]
        station_count = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    except Exception as e:
        return {"status": "error", "detail": str(e), "timestamp": now_ist().isoformat()}

    return {
        "status": "ok",
        "timestamp": now_ist().isoformat(),
        "data": {"trains_tracked": train_count, "stations_tracked": station_count},
    }
