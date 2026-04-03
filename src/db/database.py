import libsql_experimental as libsql
from pathlib import Path
from config.settings import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "schema.sql"


def get_connection() -> libsql.Connection:
    if TURSO_DATABASE_URL:
        conn = libsql.connect("local.db", sync_url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
        conn.sync()
    else:
        # Local fallback for development
        conn = libsql.connect("local.db")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables from schema.sql if they don't exist."""
    conn = get_connection()
    statements = _SCHEMA_PATH.read_text().split(";")
    for stmt in statements:
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
    if TURSO_DATABASE_URL:
        conn.sync()
