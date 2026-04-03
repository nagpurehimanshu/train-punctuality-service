"""Turso database client using HTTP pipeline API.

No Rust compilation needed. Works on Render free tier.
Falls back to local SQLite for development when TURSO_DATABASE_URL is not set.
"""

import sqlite3
from pathlib import Path
from config.settings import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "schema.sql"


class TursoConnection:
    """Wraps Turso HTTP API to look like a sqlite3 connection."""

    def __init__(self, base_url: str, token: str):
        import httpx
        self._url = f"{base_url}/v2/pipeline"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._http = httpx.Client(timeout=30)

    def execute(self, sql: str, params: tuple = ()) -> "TursoCursor":
        args = [_convert_param(p) for p in params]
        body = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": args}},
                {"type": "close"},
            ]
        }
        r = self._http.post(self._url, json=body, headers=self._headers)
        r.raise_for_status()
        result = r.json()["results"][0]
        if result["type"] == "error":
            raise ValueError(result["error"]["message"])
        return TursoCursor(result["response"]["result"])

    def executemany_stmts(self, stmts: list[tuple[str, tuple]]) -> None:
        """Execute multiple statements in one pipeline request."""
        requests = []
        for sql, params in stmts:
            args = [_convert_param(p) for p in params]
            requests.append({"type": "execute", "stmt": {"sql": sql, "args": args}})
        requests.append({"type": "close"})
        r = self._http.post(self._url, json={"requests": requests}, headers=self._headers)
        r.raise_for_status()

    def commit(self):
        pass  # Turso auto-commits

    def close(self):
        self._http.close()


class TursoCursor:
    def __init__(self, result: dict):
        self._rows = result.get("rows", [])
        self._cols = [c["name"] for c in result.get("cols", [])]

    def fetchone(self):
        if not self._rows:
            return None
        return [_extract_value(v) for v in self._rows[0]]

    def fetchall(self):
        return [[_extract_value(v) for v in row] for row in self._rows]


def _convert_param(p):
    if p is None:
        return {"type": "null", "value": None}
    if isinstance(p, int):
        return {"type": "integer", "value": str(p)}
    if isinstance(p, float):
        return {"type": "float", "value": p}
    return {"type": "text", "value": str(p)}


def _extract_value(v):
    if v is None or v.get("type") == "null":
        return None
    if v["type"] == "integer":
        return int(v["value"])
    if v["type"] == "float":
        return float(v["value"])
    return v["value"]


def get_connection():
    if TURSO_DATABASE_URL:
        base_url = TURSO_DATABASE_URL.replace("libsql://", "https://")
        return TursoConnection(base_url, TURSO_AUTH_TOKEN)
    # Local fallback
    conn = sqlite3.connect("local.db")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    for stmt in _SCHEMA_PATH.read_text().split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
