from typing import Literal, TypedDict

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
    verification: VerificationResult
    verify_attempts: int
    # human-in-the-loop
    user_notes: str  # extra context the user gave (clarifications, edit requests)
    status: Literal["running", "stopped", "approved", "done"]
    # final
    cv_path: str
