"""Smoke tests for wiring that has no better home."""

from app.profile import load_profile


def test_sample_profile_loads():
    p = load_profile()
    assert "exp-consulting-b1" in p.evidence_ids()


def test_graph_compiles():
    from app.agent.graph import build_graph

    assert "verify" in build_graph().get_graph().nodes
