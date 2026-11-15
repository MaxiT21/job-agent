"""FastAPI layer. The frontend talks only to these endpoints.

Runs are LangGraph threads persisted in SQLite. A request advances the run until it
finishes, pauses for the candidate (`waiting_for`), or fails (`error`, retryable).

  POST  /runs                      start from a URL or pasted text
  GET   /runs/{id}                 current state
  POST  /runs/{id}/resume          answer the pending question
  POST  /runs/{id}/retry           re-run the step that failed
  GET   /runs/{id}/files/{kind}    download cv | cover_letter (.docx)
  GET   /applications              tracker
  PATCH /applications/{id}         move an application through the pipeline
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langgraph.types import Command
from pydantic import ValidationError

from app import tracker
from app.agent.graph import get_graph
from app.api.models import (
    Files,
    Health,
    LLMCall,
    Resume,
    RunView,
    StartRun,
    StatusUpdate,
    Usage,
)
from app.config import settings
from app.schemas import ANSWER_MODELS

logging.basicConfig(
    level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("app.api")

app = FastAPI(title="Job Application Agent", version="0.2.0")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
)

Graph = Annotated[Any, Depends(get_graph)]
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
FILE_KEYS = {"cv": "cv_path", "cover_letter": "letter_path"}


def _config(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


def _snapshot(graph, run_id: str):
    snap = graph.get_state(_config(run_id))
    if not snap.values:
        raise HTTPException(404, "Run not found")
    return snap


def _pending(snap) -> dict | None:
    pending = [i.value for t in snap.tasks for i in t.interrupts]
    return pending[0] if pending else None


def _error(snap) -> str | None:
    return next((t.error for t in snap.tasks if t.error), None)


def _view(graph, run_id: str) -> RunView:
    snap = _snapshot(graph, run_id)
    v = snap.values
    waiting, error = _pending(snap), _error(snap)
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


def _advance(graph, run_id: str, payload) -> RunView:
    """Run the graph; a failure is recorded on the run (status=error), not raised."""
    try:
        graph.invoke(payload, _config(run_id))
    except Exception:
        log.exception("run %s failed", run_id)
    return _view(graph, run_id)


@app.get("/health", response_model=Health)
def health():
    profile = "custom" if settings.profile_path.exists() else "sample"
    return Health(ok=True, model=settings.model, profile=profile)


@app.post("/runs", response_model=RunView, status_code=201)
def start_run(body: StartRun, graph: Graph):
    run_id = str(uuid.uuid4())
    payload = {
        "posting_url": str(body.posting_url) if body.posting_url else None,
        "posting_text": body.posting_text,
    }
    return _advance(graph, run_id, {k: v for k, v in payload.items() if v})


@app.get("/runs/{run_id}", response_model=RunView)
def get_run(run_id: str, graph: Graph):
    return _view(graph, run_id)


@app.post("/runs/{run_id}/resume", response_model=RunView)
def resume_run(run_id: str, body: Resume, graph: Graph):
    pending = _pending(_snapshot(graph, run_id))
    if pending is None:
        raise HTTPException(409, "This run is not waiting for an answer")
    try:
        answer = ANSWER_MODELS[pending["type"]].model_validate(body.value)
    except ValidationError as e:
        raise HTTPException(422, e.errors(include_url=False, include_context=False)) from e
    return _advance(graph, run_id, Command(resume=answer.model_dump()))


@app.post("/runs/{run_id}/retry", response_model=RunView)
def retry_run(run_id: str, graph: Graph):
    if not _error(_snapshot(graph, run_id)):
        raise HTTPException(409, "Only failed runs can be retried")
    return _advance(graph, run_id, None)


@app.get("/runs/{run_id}/files/{kind}")
def download_file(run_id: str, kind: Literal["cv", "cover_letter"], graph: Graph):
    path = _snapshot(graph, run_id).values.get(FILE_KEYS[kind])
    if not path or not Path(path).exists():
        raise HTTPException(404, "File not generated yet")
    return FileResponse(path, media_type=DOCX, filename=Path(path).name)


@app.get("/applications", response_model=list[tracker.Application])
def list_applications():
    return tracker.list_applications()


@app.patch("/applications/{run_id}", response_model=tracker.Application)
def update_application(run_id: str, body: StatusUpdate):
    try:
        return tracker.update_status(run_id, body.status)
    except KeyError as e:
        raise HTTPException(404, "Application not found") from e
