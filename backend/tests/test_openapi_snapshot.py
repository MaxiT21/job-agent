"""The frontend's types are generated from frontend/openapi.json; it must match the API."""

import json
from pathlib import Path

from app.main import app

SNAPSHOT = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"


def test_openapi_snapshot_is_current():
    assert SNAPSHOT.exists(), "run: uv run python scripts/export_openapi.py"
    assert json.loads(SNAPSHOT.read_text()) == app.openapi(), (
        "frontend/openapi.json is stale: run `uv run python scripts/export_openapi.py`, "
        "then `npm run gen:types` in frontend/"
    )
