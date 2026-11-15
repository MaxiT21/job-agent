"""Run lifecycle shared by the API and the CLI: start, inspect, answer, retry."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.types import Command

from app.api.models import Files, LLMCall, RunView, Usage
from app.schemas import ANSWER_MODELS

log = logging.getLogger(__name__)


class RunNotFound(LookupError):
    pass


class NotWaiting(RuntimeError):
    """The run has no pending question to answer."""


class NotFailed(RuntimeError):
    """Only failed runs can be retried."""


class Runs:
    def __init__(self, graph: Any):
        self.graph = graph

    @staticmethod
    def _config(run_id: str) -> dict:
        return {"configurable": {"thread_id": run_id}}

    def _snapshot(self, run_id: str):
        snap = self.graph.get_state(self._config(run_id))
        if not snap.values:
            raise RunNotFound(run_id)
        return snap

    @staticmethod
    def _pending(snap) -> dict | None:
        pending = [i.value for t in snap.tasks for i in t.interrupts]
        return pending[0] if pending else None

    @staticmethod
    def _error(snap) -> str | None:
        return next((t.error for t in snap.tasks if t.error), None)

    def _advance(self, run_id: str, payload: Any) -> RunView:
        """Run the graph; a failure is recorded on the run (status=error), not raised."""
        try:
            self.graph.invoke(payload, self._config(run_id))
        except Exception:
            log.exception("run %s failed", run_id)
        return self.view(run_id)

    # ---------- public ----------

    def start(self, *, posting_url: str | None = None, posting_text: str | None = None) -> RunView:
        payload = {"posting_url": posting_url, "posting_text": posting_text}
        return self._advance(str(uuid.uuid4()), {k: v for k, v in payload.items() if v})

    def answer(self, run_id: str, value: dict[str, Any]) -> RunView:
        """Validate `value` against the pending question (pydantic.ValidationError if wrong)."""
        pending = self._pending(self._snapshot(run_id))
        if pending is None:
            raise NotWaiting(run_id)
        answer = ANSWER_MODELS[pending["type"]].model_validate(value)
        return self._advance(run_id, Command(resume=answer.model_dump()))

    def retry(self, run_id: str) -> RunView:
        if not self._error(self._snapshot(run_id)):
            raise NotFailed(run_id)
        return self._advance(run_id, None)

    def file_path(self, run_id: str, kind: str) -> str | None:
        key = {"cv": "cv_path", "cover_letter": "letter_path"}[kind]
        return self._snapshot(run_id).values.get(key)

    def view(self, run_id: str) -> RunView:
        snap = self._snapshot(run_id)
        v = snap.values
        waiting, error = self._pending(snap), self._error(snap)
        if error:
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
            status=status,
            waiting_for=waiting,
            error=error,
            posting=v.get("posting"),
            fit=v.get("fit"),
            cv=v.get("cv"),
            cover_letter=v.get("cover_letter"),
            verification=v.get("verification"),
            files=Files(cv=bool(v.get("cv_path")), cover_letter=bool(v.get("letter_path"))),
            usage=Usage(
                calls=calls,
                total_cost_usd=round(sum(c.cost_usd or 0 for c in calls), 6),
                total_latency_s=round(sum(c.latency_s for c in calls), 3),
            ),
        )
