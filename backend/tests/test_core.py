"""Smoke tests for wiring that has no better home."""

from app.profile import load_profile


def test_sample_profile_loads():
    p = load_profile()
    assert "exp-consulting-b1" in p.evidence_ids()


def test_graph_compiles():
    from app.agent.graph import build_graph

    assert "verify" in build_graph().get_graph().nodes


def test_graph_declares_every_route():
    """Conditional edges list their targets, so the graph can be drawn and inspected."""
    from app.agent.graph import build_graph

    edges = {(e.source, e.target) for e in build_graph().get_graph().edges}
    expected = {
        ("fetch_posting", "ask_for_text"),
        ("fetch_posting", "extract_requirements"),
        ("extract_requirements", "ask_clarification"),
        ("extract_requirements", "match_profile"),
        ("match_profile", "confirm_low_fit"),
        ("match_profile", "tailor_cv"),
        ("confirm_low_fit", "__end__"),
        ("confirm_low_fit", "tailor_cv"),
        ("tailor_cv", "write_cover_letter"),
        ("tailor_cv", "verify"),
        ("verify", "tailor_cv"),
        ("verify", "write_cover_letter"),
        ("verify", "human_approval"),
        ("human_approval", "render_and_log"),
        ("human_approval", "tailor_cv"),
        ("render_and_log", "__end__"),
    }
    assert expected <= edges
