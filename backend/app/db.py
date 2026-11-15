"""SQLite connections. One file holds LangGraph checkpoints and the application tracker.

Swap point for Postgres/Supabase later: `build_persistent_graph` and `tracker` are the
only consumers.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
