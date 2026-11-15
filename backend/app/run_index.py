"""Which runs exist and when they started (LangGraph checkpoints don't list threads cheaply)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from app.config import settings
from app.db import connect

_SCHEMA = "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL)"


def _conn() -> sqlite3.Connection:
    conn = connect(settings.database_path)
    conn.execute(_SCHEMA)
    return conn


def register(run_id: str) -> None:
    with closing(_conn()) as conn, conn:
        conn.execute(
            "INSERT OR IGNORE INTO runs VALUES (?, ?)", (run_id, datetime.now(UTC).isoformat())
        )


def created_at(run_id: str) -> datetime | None:
    with closing(_conn()) as conn:
        row = conn.execute("SELECT created_at FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return datetime.fromisoformat(row[0]) if row else None


def recent(limit: int) -> list[str]:
    with closing(_conn()) as conn:
        rows = conn.execute(
            "SELECT run_id FROM runs ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
        )
        return [r[0] for r in rows]
