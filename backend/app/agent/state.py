import operator
from typing import Annotated, Literal, TypedDict

from app.schemas import (
    CoverLetter,
    FitReport,
    JobPosting,
    TailoredCV,
    VerificationResult,
)


class AgentState(TypedDict, total=False):
    # input
    posting_url: str | None
    posting_text: str
    # pipeline outputs
    posting: JobPosting
    fit: FitReport
    cv: TailoredCV
    cover_letter: CoverLetter
    verification: VerificationResult | None
    verify_attempts: int
    regenerate: list[Literal["cv", "letter"]]  # what the next generation pass must redo
    # human-in-the-loop
    clarifications: Annotated[list[str], operator.add]  # answers about the posting; kept all run
    edit_notes: str | None  # latest change request from the approval step
    status: Literal["running", "stopped", "approved", "done"]
    # final
    cv_path: str
    letter_path: str
    # observability: one dict per LLM call (see app.llm.CallRecord), appended by each node
    llm_calls: Annotated[list[dict], operator.add]
