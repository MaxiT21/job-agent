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
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app import tracker
from app.agent.graph import get_graph
from app.api.models import Health, Resume, RunView, StartRun, StatusUpdate
from app.config import settings
from app.runs import NotFailed, NotWaiting, RunNotFound, Runs

logging.basicConfig(
    level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

app = FastAPI(title="Job Application Agent", version="0.2.0")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
)

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def get_runs(graph: Annotated[Any, Depends(get_graph)]) -> Runs:
    return Runs(graph)


RunsDep = Annotated[Runs, Depends(get_runs)]


@contextmanager
def _http_errors():
    try:
        yield
    except RunNotFound as e:
        raise HTTPException(404, "Run not found") from e
    except NotWaiting as e:
        raise HTTPException(409, "This run is not waiting for an answer") from e
    except NotFailed as e:
        raise HTTPException(409, "Only failed runs can be retried") from e
    except ValidationError as e:
        raise HTTPException(422, e.errors(include_url=False, include_context=False)) from e


@app.get("/health", response_model=Health)
def health():
    profile = "custom" if settings.profile_path.exists() else "sample"
    return Health(ok=True, model=settings.model, profile=profile)


@app.post("/runs", response_model=RunView, status_code=201)
def start_run(body: StartRun, runs: RunsDep):
    url = str(body.posting_url) if body.posting_url else None
    return runs.start(posting_url=url, posting_text=body.posting_text)


@app.get("/runs/{run_id}", response_model=RunView)
def get_run(run_id: str, runs: RunsDep):
    with _http_errors():
        return runs.view(run_id)


@app.post("/runs/{run_id}/resume", response_model=RunView)
def resume_run(run_id: str, body: Resume, runs: RunsDep):
    with _http_errors():
        return runs.answer(run_id, body.value)


@app.post("/runs/{run_id}/retry", response_model=RunView)
def retry_run(run_id: str, runs: RunsDep):
    with _http_errors():
        return runs.retry(run_id)


@app.get("/runs/{run_id}/files/{kind}")
def download_file(run_id: str, kind: Literal["cv", "cover_letter"], runs: RunsDep):
    with _http_errors():
        path = runs.file_path(run_id, kind)
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
