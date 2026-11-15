"""Pydantic schemas: the contract between every step of the agent.

Design rule: every sentence the agent writes (CV bullet, cover-letter paragraph)
carries the IDs of the profile items that back it. The verifier uses those IDs
to guarantee nothing is invented.
"""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ---------- Job posting ----------


class Language(StrEnum):
    en = "en"
    es = "es"
    ca = "ca"


class Requirement(BaseModel):
    id: str = Field(description="Short stable id, e.g. 'r1', 'r2'")
    text: str = Field(description="The requirement in one short sentence")
    category: Literal["skill", "experience", "education", "language", "other"]
    importance: Literal["must", "nice"]


class JobPosting(BaseModel):
    title: str
    company: str
    location: str | None = None
    seniority: Literal["intern", "junior", "mid", "senior", "unknown"] = "unknown"
    language: Language = Field(Language.en, description="Language the posting is written in")
    requirements: list[Requirement]
    responsibilities: list[str] = []
    is_vague: bool = Field(
        False,
        description="True if the posting is too vague to tailor an application (no clear requirements)",
    )
    clarifying_question: str | None = Field(
        None, description="If is_vague, one question to ask the candidate"
    )


# ---------- Candidate profile (single source of truth) ----------


class Bullet(BaseModel):
    id: str
    text: str
    tags: list[str] = []


class ProfileItem(BaseModel):
    id: str
    kind: Literal["experience", "project", "education", "skill", "certificate", "language"]
    title: str
    org: str | None = None
    period: str | None = Field(None, coerce_numbers_to_str=True)
    location: str | None = None
    bullets: list[Bullet] = []
    tags: list[str] = []


# The profile's own `summary` field is citable evidence under this reserved ID.
SUMMARY_ID = "summary"


class Profile(BaseModel):
    name: str
    email: str
    phone: str | None = None
    location: str
    links: dict[str, str] = {}
    summary: str
    items: list[ProfileItem]

    @model_validator(mode="after")
    def _ids_are_unique(self) -> Profile:
        counts = Counter(i for item in self.items for i in [item.id, *(b.id for b in item.bullets)])
        if dupes := sorted(i for i, n in counts.items() if n > 1):
            raise ValueError(f"Profile IDs must be unique; duplicated: {dupes}")
        if SUMMARY_ID in counts:
            raise ValueError(
                f"'{SUMMARY_ID}' is reserved for the profile summary; rename that item"
            )
        return self

    def evidence_ids(self) -> set[str]:
        """All IDs (summary + items + bullets) that generated text is allowed to cite."""
        ids: set[str] = {SUMMARY_ID}
        for item in self.items:
            ids.add(item.id)
            ids.update(b.id for b in item.bullets)
        return ids

    def item(self, item_id: str) -> ProfileItem | None:
        return next((i for i in self.items if i.id == item_id), None)

    def owner(self, evidence_id: str) -> ProfileItem | None:
        """The item an ID belongs to: the item itself, or the item holding that bullet."""
        for item in self.items:
            if item.id == evidence_id or any(b.id == evidence_id for b in item.bullets):
                return item
        return None

    def evidence_text(self, evidence_id: str) -> str:
        """Everything a citation of this ID may rely on (used for the number check).

        Citing an item covers all its bullets; citing a bullet covers that bullet plus
        its item's header (title, org, period, location).
        """
        if evidence_id == SUMMARY_ID:
            return self.summary
        item = self.owner(evidence_id)
        if item is None:
            return ""
        header = " ".join(filter(None, [item.title, item.org, item.period, item.location]))
        if evidence_id == item.id:
            return " ".join([header, *item.tags, *(b.text for b in item.bullets)])
        bullet = next(b for b in item.bullets if b.id == evidence_id)
        return f"{header} {bullet.text}"


# ---------- Matching ----------


class RequirementMatch(BaseModel):
    requirement_id: str
    status: Literal["met", "partial", "gap"]
    evidence_ids: list[str] = Field(default_factory=list, description="Profile IDs that support it")
    note: str = Field(description="One line explaining the judgement")


class MatchResult(BaseModel):
    """What the LLM returns. The score is computed in code, not by the LLM."""

    matches: list[RequirementMatch]
    summary: str


class FitReport(BaseModel):
    matches: list[RequirementMatch]
    summary: str
    score: float = Field(ge=0, le=100)


# ---------- Generated outputs ----------


class GroundedLine(BaseModel):
    text: str
    evidence_ids: list[str] = Field(
        description="Profile IDs this sentence is based on. Never empty."
    )


class CVEntry(BaseModel):
    item_id: str = Field(description="ID of the profile item (experience/project/education)")
    bullets: list[GroundedLine]


class TailoredCV(BaseModel):
    summary: GroundedLine
    entries: list[CVEntry] = Field(description="Ordered by relevance to the posting")
    skills: list[str] = Field(description="Only skills present in the profile")


class CoverLetter(BaseModel):
    paragraphs: list[GroundedLine]


# ---------- Verification ----------


class VerificationIssue(BaseModel):
    where: str = Field(description="e.g. 'cv.entries[0].bullets[1]' or 'cover_letter[2]'")
    text: str
    reason: str


class VerificationResult(BaseModel):
    passed: bool
    issues: list[VerificationIssue] = []


# ---------- Human-in-the-loop: what the agent asks (interrupt payloads) ----------


class PasteTextRequest(BaseModel):
    """The URL could not be read; ask the candidate to paste the posting."""

    type: Literal["paste_text"] = "paste_text"
    reason: str


class ClarifyRequest(BaseModel):
    """The posting is too vague to tailor an application."""

    type: Literal["clarify"] = "clarify"
    question: str | None


class LowFitRequest(BaseModel):
    """The fit score is below the threshold: apply anyway?"""

    type: Literal["low_fit"] = "low_fit"
    score: float
    gaps: list[str] = Field(description="IDs of requirements with no supporting evidence")
    summary: str


class ApprovalRequest(BaseModel):
    """Final review before rendering the documents."""

    type: Literal["approve"] = "approve"
    fit: FitReport
    cv: TailoredCV
    cover_letter: CoverLetter | None
    verification: VerificationResult


# ---------- Human-in-the-loop: how the candidate answers (resume payloads) ----------


class PasteTextAnswer(BaseModel):
    text: str = Field(min_length=1)


class ClarifyAnswer(BaseModel):
    answer: str = Field(min_length=1)


class LowFitAnswer(BaseModel):
    proceed: bool


class ApprovalAnswer(BaseModel):
    """Rejecting with notes regenerates both documents with those notes."""

    approved: bool
    notes: str = ""


ANSWER_MODELS: dict[str, type[BaseModel]] = {
    "paste_text": PasteTextAnswer,
    "clarify": ClarifyAnswer,
    "low_fit": LowFitAnswer,
    "approve": ApprovalAnswer,
}


# Types stored in the LangGraph checkpoint (allow-listed for deserialization).
__all_state_types__ = [
    "Language",
    "Requirement",
    "JobPosting",
    "RequirementMatch",
    "FitReport",
    "GroundedLine",
    "CVEntry",
    "TailoredCV",
    "CoverLetter",
    "VerificationIssue",
    "VerificationResult",
]
