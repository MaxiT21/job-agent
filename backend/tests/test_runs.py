"""Run lifecycle: background execution, progress, locking, restart recovery, listing."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.agent.graph import build_graph
from app.runs import Busy, Runs
from tests.fakes import happy_script, match, posting

TEXT = "We need a Python + SQL intern. Kubernetes is a plus. Barcelona, hybrid."


@pytest.fixture
def pool():
    with ThreadPoolExecutor(max_workers=2) as ex:
        yield ex


def settle(runs: Runs, run_id: str, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while (view := runs.view(run_id)).status == "running":
        assert time.monotonic() < deadline, "run did not settle"
        time.sleep(0.02)
    return view


def blocking_match(release: threading.Event):
    def respond():
        assert release.wait(5), "test never released the step"
        return match("met", "met", "gap")

    return respond


def test_start_returns_running_then_settles(fake_llm, pool):
    release = threading.Event()
    fake_llm(happy_script(match=[blocking_match(release)]))
    runs = Runs(build_graph(), executor=pool)

    view = runs.start(posting_text=TEXT)
    assert view.status == "running"

    release.set()
    assert settle(runs, view.run_id).waiting_for.type == "approve"


def test_progress_step_reported(fake_llm, pool):
    release = threading.Event()
    fake_llm(happy_script(match=[blocking_match(release)]))
    runs = Runs(build_graph(), executor=pool)
    run_id = runs.start(posting_text=TEXT).run_id

    deadline = time.monotonic() + 5
    while runs.view(run_id).step != "match_profile":
        assert time.monotonic() < deadline
        time.sleep(0.01)
    release.set()
    assert settle(runs, run_id).step is None


def test_resume_while_running_409(fake_llm, pool):
    release = threading.Event()
    fake_llm(happy_script(match=[blocking_match(release)]))
    runs = Runs(build_graph(), executor=pool)
    run_id = runs.start(posting_text=TEXT).run_id

    with pytest.raises(Busy):
        runs.answer(run_id, {"approved": True})
    with pytest.raises(Busy):
        runs.retry(run_id)
    release.set()
    settle(runs, run_id)


def test_interrupted_run_is_retryable(fake_llm):
    """A checkpoint left mid-pipeline by a dead process (no error, no question pending)."""
    fake_llm(happy_script())
    graph = build_graph()
    runs = Runs(graph)
    cfg = {"configurable": {"thread_id": "crashed"}}
    graph.update_state(cfg, {"posting_text": TEXT, "status": "running"}, as_node="fetch_posting")

    view = runs.view("crashed")
    assert view.status == "error"
    assert "Interrupted" in view.error

    assert runs.retry("crashed").waiting_for.type == "approve"


def test_list_runs_newest_first(fake_llm):
    fake_llm(happy_script(extract=[posting(), posting(language="es")]))
    runs = Runs(build_graph())
    first = runs.start(posting_text=TEXT).run_id
    second = runs.start(posting_text=TEXT).run_id

    listed = runs.list()

    assert [r.run_id for r in listed] == [second, first]
    assert listed[0].company == "Acme"
    assert listed[0].status == "waiting"
    assert listed[0].fit_score == 80.0
