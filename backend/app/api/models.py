"""Request/response models of the HTTP API (the frontend's contract, published via OpenAPI)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.schemas import (
    ApprovalRequest,
    ClarifyRequest,
    CoverLetter,
    FitReport,
    JobPosting,
    LowFitRequest,
    PasteTextRequest,
    TailoredCV,
    VerificationResult,
)
from app.tracker import Status

WaitingFor = Annotated[
    PasteTextRequest | ClarifyRequest | LowFitRequest | ApprovalRequest,
    Field(discriminator="type"),
]


class StartRun(BaseModel):
    posting_url: HttpUrl | None = None
    posting_text: str | None = Field(None, min_length=50, max_length=50_000)

    @model_validator(mode="after")
    def exactly_one_input(self) -> StartRun:
        if bool(self.posting_url) == bool(self.posting_text):
            raise ValueError("Provide exactly one of posting_url or posting_text")
        return self


class Resume(BaseModel):
    """Answer to the pending question; its shape depends on `waiting_for.type`."""

    value: dict[str, Any]


class LLMCall(BaseModel):
    step: str
    model: str
    latency_s: float
    cost_usd: float | None
    ok: bool


class Usage(BaseModel):
    calls: list[LLMCall]
    total_cost_usd: float
    total_latency_s: float


class Files(BaseModel):
    cv: bool
    cover_letter: bool


RunStatus = Literal["running", "waiting", "stopped", "done", "error"]


class RunView(BaseModel):
    run_id: str
    created_at: datetime | None = None
    status: RunStatus
    step: str | None = Field(None, description="Graph node running next, while status=running")
    waiting_for: WaitingFor | None = None
    error: str | None = None
    posting: JobPosting | None = None
    fit: FitReport | None = None
    cv: TailoredCV | None = None
    cover_letter: CoverLetter | None = None
    verification: VerificationResult | None = None
    files: Files
    usage: Usage


class RunSummary(BaseModel):
    run_id: str
    created_at: datetime | None
    status: RunStatus
    company: str | None
    title: str | None
    fit_score: float | None


class StatusUpdate(BaseModel):
    status: Status


class Health(BaseModel):
    ok: bool
    model: str
    profile: Literal["custom", "sample"]
