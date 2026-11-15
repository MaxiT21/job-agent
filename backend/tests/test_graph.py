"""End-to-end graph behaviour with a scripted LLM (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.types import Command
from pydantic import ValidationError

from app.agent.graph import build_graph
from tests.fakes import happy_script, match, posting, verify_fail

POSTING = {"posting_text": "We need a Python + SQL intern. Kubernetes is a plus."}


@pytest.fixture
def graph():
    return build_graph()


def waiting_for(graph, thread) -> dict | None:
    snap = graph.get_state(thread)
    pending = [i.value for t in snap.tasks for i in t.interrupts]
    return pending[0] if pending else None


def test_happy_path_pauses_for_approval_then_renders(graph, thread, fake_llm):
    llm = fake_llm(happy_script())

    graph.invoke(POSTING, thread)
    assert waiting_for(graph, thread)["type"] == "approve"
    assert llm.steps() == ["extract", "match", "tailor_cv", "cover_letter", "verify"]

    graph.invoke(Command(resume={"approved": True}), thread)
    values = graph.get_state(thread).values
    assert values["status"] == "done"
    assert Path(values["cv_path"]).exists()
    assert waiting_for(graph, thread) is None


def test_vague_posting_asks_and_reextracts_with_answer(graph, thread, fake_llm):
    llm = fake_llm(happy_script(extract=[posting(vague=True), posting()]))

    graph.invoke(POSTING, thread)
    question = waiting_for(graph, thread)
    assert question == {"type": "clarify", "question": "What stack does the team use?"}

    graph.invoke(Command(resume={"answer": "Python and Postgres"}), thread)
    assert "Python and Postgres" in llm.prompts("extract")[1]
    assert waiting_for(graph, thread)["type"] == "approve"


def test_low_fit_stop_ends_run(graph, thread, fake_llm):
    llm = fake_llm(happy_script(match=[match("gap", "gap", "gap")]))

    graph.invoke(POSTING, thread)
    assert waiting_for(graph, thread)["type"] == "low_fit"

    graph.invoke(Command(resume={"proceed": False}), thread)
    assert graph.get_state(thread).values["status"] == "stopped"
    assert "tailor_cv" not in llm.steps()


def test_low_fit_proceed_continues(graph, thread, fake_llm):
    fake_llm(happy_script(match=[match("gap", "gap", "gap")]))

    graph.invoke(POSTING, thread)
    graph.invoke(Command(resume={"proceed": True}), thread)
    assert waiting_for(graph, thread)["type"] == "approve"


def test_failed_verification_retries_then_escalates(graph, thread, fake_llm):
    # Default max_verify_retries=2: 1 generation + 2 retries, then the human decides.
    llm = fake_llm(happy_script(verify=[verify_fail(reason="Invents a team size")]))

    graph.invoke(POSTING, thread)
    assert llm.steps().count("tailor_cv") == 3
    assert llm.steps().count("verify") == 3
    assert "Invents a team size" in llm.prompts("tailor_cv")[1]
    pending = waiting_for(graph, thread)
    assert pending["type"] == "approve"
    assert pending["verification"]["passed"] is False


def test_edit_notes_regenerate_and_keep_clarification(graph, thread, fake_llm):
    llm = fake_llm(happy_script(extract=[posting(vague=True), posting()]))

    graph.invoke(POSTING, thread)
    graph.invoke(Command(resume={"answer": "Python and Postgres"}), thread)
    graph.invoke(Command(resume={"approved": False, "notes": "Shorter summary"}), thread)

    regenerated = llm.prompts("tailor_cv")[-1]
    assert "Shorter summary" in regenerated
    assert "Python and Postgres" in regenerated
    assert waiting_for(graph, thread)["type"] == "approve"


def test_resume_answers_are_validated(graph, thread, fake_llm):
    fake_llm(happy_script())
    graph.invoke(POSTING, thread)

    with pytest.raises(ValidationError):
        graph.invoke(Command(resume="yes"), thread)
