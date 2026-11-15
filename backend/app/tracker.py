"""Application tracker: one row per approved run (SQLite now; Postgres/Supabase later).

The agent only writes "ready"; the candidate moves applications through the pipeline
themselves (the agent never submits anything).
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.config import settings
from app.db import connect
from app.schemas import JobPosting

Status = Literal["ready", "applied", "interview", "offer", "rejected", "withdrawn"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    run_id      TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    company     TEXT NOT NULL,
    title       TEXT NOT NULL,
    location    TEXT,
    fit_score   REAL NOT NULL,
    cv_path     TEXT NOT NULL,
    letter_path TEXT,
    status      TEXT NOT NULL DEFAULT 'ready'
)
"""


class Application(BaseModel):
    run_id: str
    created_at: datetime
    company: str
    title: str
    location: str | None
    fit_score: float
    cv_path: str
    letter_path: str | None
    status: Status


def _conn() -> sqlite3.Connection:
    conn = connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def log_application(
    run_id: str,
    posting: JobPosting,
    fit_score: float,
    cv_path: Path | str,
    letter_path: Path | str | None,
) -> None:
    """Idempotent: re-running the final node for the same run updates the same row."""
    with closing(_conn()) as conn, conn:
        conn.execute(
            """
            INSERT INTO applications
                (run_id, created_at, company, title, location, fit_score, cv_path, letter_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                fit_score = excluded.fit_score,
                cv_path = excluded.cv_path,
                letter_path = excluded.letter_path
            """,
            (
                run_id,
                datetime.now(UTC).isoformat(),
                posting.company,
                posting.title,
                posting.location,
                fit_score,
                str(cv_path),
                str(letter_path) if letter_path else None,
            ),
        )


def list_applications() -> list[Application]:
    with closing(_conn()) as conn:
        rows = conn.execute("SELECT * FROM applications ORDER BY created_at DESC, rowid DESC")
        return [Application(**dict(r)) for r in rows]


def update_status(run_id: str, status: Status) -> Application:
    with closing(_conn()) as conn, conn:
        cur = conn.execute("UPDATE applications SET status = ? WHERE run_id = ?", (status, run_id))
        if cur.rowcount == 0:
            raise KeyError(run_id)
        row = conn.execute("SELECT * FROM applications WHERE run_id = ?", (run_id,)).fetchone()
        return Application(**dict(row))
