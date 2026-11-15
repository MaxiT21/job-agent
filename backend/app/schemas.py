"""Pydantic schemas: the contract between every step of the agent.

Design rule: every sentence the agent writes (CV bullet, cover-letter paragraph)
carries the IDs of the profile items that back it. The verifier uses those IDs
to guarantee nothing is invented.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------- Job posting ----------

class Language(str, Enum):
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


class Profile(BaseModel):
    name: str
    email: str
    phone: str | None = None
    location: str
    links: dict[str, str] = {}
    summary: str
    items: list[ProfileItem]

    def evidence_ids(self) -> set[str]:
        """All IDs (items + bullets) that generated text is allowed to cite."""
        ids: set[str] = set()
        for item in self.items:
            ids.add(item.id)
            ids.update(b.id for b in item.bullets)
        return ids

    def item(self, item_id: str) -> ProfileItem | None:
        return next((i for i in self.items if i.id == item_id), None)


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
    evidence_ids: list[str] = Field(description="Profile IDs this sentence is based on. Never empty.")


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


# Types stored in the LangGraph checkpoint (allow-listed for deserialization).
__all_state_types__ = [
    "Language", "Requirement", "JobPosting", "RequirementMatch", "FitReport",
    "GroundedLine", "CVEntry", "TailoredCV", "CoverLetter",
    "VerificationIssue", "VerificationResult",
]
