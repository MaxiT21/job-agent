"""Run lifecycle shared by the API and the CLI: start, inspect, answer, retry, list.

Runs execute inline (CLI, tests) or on an executor (API): with an executor, `start`,
`answer` and `retry` return immediately with `status="running"` and the caller polls `view`.
Only one execution per run can be in flight at a time.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import Executor
from typing import Any

from langgraph.types import Command

from app import run_index
from app.api.models import Files, LLMCall, RunSummary, RunView, Usage
from app.schemas import ANSWER_MODELS

log = logging.getLogger(__name__)

INTERRUPTED = "Interrupted (the server stopped mid-run). Retry to continue."

# Process-wide: run ids are unique, and the API builds a Runs object per request.
_lock = threading.Lock()
_inflight: set[str] = set()
_steps: dict[str, str | None] = {}


class RunNotFound(LookupError):
    pass


class NotWaiting(RuntimeError):
    """The run has no pending question to answer."""


class NotFailed(RuntimeError):
    """Only failed or interrupted runs can be retried."""


class Busy(RuntimeError):
    """The run is executing; wait until it pauses or finishes."""


class Runs:
    def __init__(self, graph: Any, executor: Executor | None = None):
        self.graph = graph
        self.executor = executor

    @staticmethod
    def _config(run_id: str) -> dict:
        return {"configurable": {"thread_id": run_id}}

    def _snapshot(self, run_id: str):
        snap = self.graph.get_state(self._config(run_id))
        if not snap.values and run_id not in _inflight:
            raise RunNotFound(run_id)
        return snap

    @staticmethod
    def _pending(snap) -> dict | None:
        pending = [i.value for t in snap.tasks for i in t.interrupts]
        return pending[0] if pending else None

    @staticmethod
    def _error(snap) -> str | None:
        return next((t.error for t in snap.tasks if t.error), None)

    def _failure(self, run_id: str, snap) -> str | None:
        """Error text if the run failed or was left mid-pipeline by a dead process."""
        if run_id in _inflight:
            return None
        if error := self._error(snap):
            return error
        if snap.values and snap.next and not self._pending(snap):
            return INTERRUPTED
        return None

    def _execute(self, run_id: str, payload: Any) -> None:
        cfg = self._config(run_id)
        try:
            for event in self.graph.stream(payload, cfg, stream_mode="tasks"):
                if "result" not in event:  # a node is starting
                    _steps[run_id] = event["name"]
        except Exception:
            log.exception("run %s failed", run_id)
        finally:
            with _lock:
                _inflight.discard(run_id)
                _steps.pop(run_id, None)

    def _advance(self, run_id: str, payload: Any) -> RunView:
        with _lock:
            if run_id in _inflight:
                raise Busy(run_id)
            _inflight.add(run_id)
            _steps[run_id] = None
        if self.executor is None:
            self._execute(run_id, payload)
        else:
            self.executor.submit(self._execute, run_id, payload)
        return self.view(run_id)

    # ---------- public ----------

    def start(self, *, posting_url: str | None = None, posting_text: str | None = None) -> RunView:
        run_id = str(uuid.uuid4())
        run_index.register(run_id)
        payload = {"posting_url": posting_url, "posting_text": posting_text}
        return self._advance(run_id, {k: v for k, v in payload.items() if v})

    def answer(self, run_id: str, value: dict[str, Any]) -> RunView:
        """Validate `value` against the pending question (pydantic.ValidationError if wrong)."""
        if run_id in _inflight:
            raise Busy(run_id)
        pending = self._pending(self._snapshot(run_id))
        if pending is None:
            raise NotWaiting(run_id)
        answer = ANSWER_MODELS[pending["type"]].model_validate(value)
        return self._advance(run_id, Command(resume=answer.model_dump()))

    def retry(self, run_id: str) -> RunView:
        if run_id in _inflight:
            raise Busy(run_id)
        if not self._failure(run_id, self._snapshot(run_id)):
            raise NotFailed(run_id)
        return self._advance(run_id, None)

    def file_path(self, run_id: str, kind: str) -> str | None:
        key = {"cv": "cv_path", "cover_letter": "letter_path"}[kind]
        return self._snapshot(run_id).values.get(key)

    def list(self, limit: int = 20) -> list[RunSummary]:
        out = []
        for run_id in run_index.recent(limit):
            try:
                v = self.view(run_id)
            except RunNotFound:
                continue
            out.append(
                RunSummary(
                    run_id=run_id,
                    created_at=v.created_at,
                    status=v.status,
                    company=v.posting.company if v.posting else None,
                    title=v.posting.title if v.posting else None,
                    fit_score=v.fit.score if v.fit else None,
                )
            )
        return out

    def view(self, run_id: str) -> RunView:
        snap = self._snapshot(run_id)
        v = snap.values
        waiting, error = self._pending(snap), self._failure(run_id, snap)
        if run_id in _inflight:
            status = "running"
        elif error:
            status = "error"
        elif waiting:
            status = "waiting"
        elif v.get("status") in ("stopped", "done"):
            status = v["status"]
        else:
            status = "running"
        calls = [LLMCall(**c) for c in v.get("llm_calls", [])]
        return RunView(
            run_id=run_id,
            created_at=run_index.created_at(run_id),
            status=status,
            step=_steps.get(run_id),
            waiting_for=waiting if status == "waiting" else None,
            error=error,
            posting=v.get("posting"),
            fit=v.get("fit"),
            cv=v.get("cv"),
            cover_letter=v.get("cover_letter"),
            verification=v.get("verification"),
            verification_history=v.get("verification_history", []),
            files=Files(cv=bool(v.get("cv_path")), cover_letter=bool(v.get("letter_path"))),
            usage=Usage(
                calls=calls,
                total_cost_usd=round(sum(c.cost_usd or 0 for c in calls), 6),
                total_latency_s=round(sum(c.latency_s for c in calls), 3),
            ),
        )
