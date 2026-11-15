"""FastAPI layer. The Next.js frontend talks only to these endpoints.

Flow:
  POST /runs                 -> starts a run, returns either an interrupt (question for the user) or the result
  POST /runs/{id}/resume     -> answers the interrupt, returns the next interrupt or the result
  GET  /runs/{id}/cv         -> downloads the generated .docx
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langgraph.types import Command
from pydantic import BaseModel, model_validator

from app.agent.graph import graph
from app.config import settings
from app.llm import usage

app = FastAPI(title="Job Application Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
)


class StartRun(BaseModel):
    posting_url: str | None = None
    posting_text: str | None = None

    @model_validator(mode="after")
    def one_input(self):
        if not (self.posting_url or self.posting_text):
            raise ValueError("Provide posting_url or posting_text")
        return self


class Resume(BaseModel):
    value: dict[str, Any] | str


def _config(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


def _snapshot(run_id: str) -> dict:
    snap = graph.get_state(_config(run_id))
    if not snap.values:
        raise HTTPException(404, "Run not found")
    interrupts = [i.value for task in snap.tasks for i in task.interrupts]
    values = snap.values
    return {
        "run_id": run_id,
        "status": values.get("status"),
        "waiting_for": interrupts[0] if interrupts else None,
        "fit": values["fit"].model_dump() if values.get("fit") else None,
        "cv_ready": bool(values.get("cv_path")),
        "cost_usd": round(usage.total_cost, 4),
    }


@app.get("/health")
def health():
    return {"ok": True, "model": settings.model}


@app.post("/runs")
def start_run(body: StartRun):
    run_id = str(uuid.uuid4())
    graph.invoke(body.model_dump(exclude_none=True), _config(run_id))
    return _snapshot(run_id)


@app.post("/runs/{run_id}/resume")
def resume_run(run_id: str, body: Resume):
    _snapshot(run_id)  # 404 if missing
    graph.invoke(Command(resume=body.value), _config(run_id))
    return _snapshot(run_id)


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    return _snapshot(run_id)


@app.get("/runs/{run_id}/cv")
def download_cv(run_id: str):
    path = graph.get_state(_config(run_id)).values.get("cv_path")
    if not path:
        raise HTTPException(404, "CV not generated yet")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=path.split("/")[-1],
    )
