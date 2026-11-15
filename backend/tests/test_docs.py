"""Docs that describe code must match the code."""

import re
from pathlib import Path

from app.agent.graph import mermaid

DOCS = Path(__file__).resolve().parents[2] / "docs"


def test_architecture_diagram_matches_the_graph():
    doc = (DOCS / "architecture.md").read_text()
    block = re.search(r"<!-- graph:start.*?```mermaid\n(.*?)```\n<!-- graph:end -->", doc, re.S)
    assert block, "graph markers missing in docs/architecture.md"
    assert block.group(1).strip() == mermaid().strip(), (
        "docs/architecture.md is stale: regenerate with `uv run python -m app.agent.graph`"
    )
