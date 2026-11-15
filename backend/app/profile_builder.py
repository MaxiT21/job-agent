"""Profile builder: guided questions -> the candidate's answers -> structured Profile draft.

Same principle as the agent: the AI only organises what the candidate wrote. IDs are
assigned in code, and anything in the draft that the answers don't support (numbers,
organisations) is flagged for the candidate to fix in the review screen.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.agent import prompts
from app.config import settings
from app.db import connect
from app.llm import structured
from app.schemas import Bullet, Profile, ProfileItem
from app.scoring import numbers_in

# ---------- guided questions ----------


class GuidedSection(BaseModel):
    id: str
    title: str
    prompt: str
    hints: list[str]
    optional: bool = False


GUIDED_SECTIONS: list[GuidedSection] = [
    GuidedSection(
        id="basics",
        title="About you",
        prompt="Your name, contact details and what you are looking for.",
        hints=[
            "Full name, email, phone (optional), city",
            "Links: GitHub, LinkedIn, portfolio",
            "Current situation (studying X, working as Y) and the roles you want",
        ],
    ),
    GuidedSection(
        id="experience",
        title="Work experience",
        prompt="Jobs and internships, most recent first. Write freely, one per paragraph.",
        hints=[
            "Company, role, dates (month and year) and city",
            "What you did and which tools you used",
            "Results with numbers if you have them (users, time saved, size of the team)",
        ],
    ),
    GuidedSection(
        id="projects",
        title="Projects",
        prompt="Personal, university or open-source projects.",
        hints=[
            "What it does and why you built it",
            "Your role and the technologies",
            "Anything measurable (users, stars, performance) and a link",
        ],
    ),
    GuidedSection(
        id="education",
        title="Education",
        prompt="Degrees and other formal education.",
        hints=["Degree, institution, dates", "Relevant courses, thesis or a good grade"],
    ),
    GuidedSection(
        id="skills",
        title="Skills",
        prompt="Languages, frameworks and tools you can actually work with.",
        hints=[
            "Only what you could discuss in an interview",
            "Say where you used each one if it isn't obvious from above",
        ],
    ),
    GuidedSection(
        id="languages",
        title="Languages",
        prompt="Languages you speak and your level.",
        hints=["e.g. Spanish (native), English (C1), Catalan (B2)"],
    ),
    GuidedSection(
        id="achievements",
        title="Certificates and achievements",
        prompt="Courses, certificates, awards, hackathons, volunteering.",
        hints=["Name, issuer and year"],
        optional=True,
    ),
    GuidedSection(
        id="cv_text",
        title="Your current CV (optional)",
        prompt="Paste the text of your current CV; it is used together with your answers.",
        hints=["Copy-paste from the PDF or Word file; formatting does not matter"],
        optional=True,
    ),
]

# ---------- saved answers ----------

_SCHEMA = """CREATE TABLE IF NOT EXISTS profile_answers (
    section_id TEXT PRIMARY KEY, text TEXT NOT NULL, updated_at TEXT NOT NULL)"""


def _conn() -> sqlite3.Connection:
    conn = connect(settings.database_path)
    conn.execute(_SCHEMA)
    return conn


def get_answers() -> dict[str, str]:
    with closing(_conn()) as conn:
        return dict(conn.execute("SELECT section_id, text FROM profile_answers ORDER BY rowid"))


def save_answers(answers: dict[str, str]) -> None:
    now = datetime.now(UTC).isoformat()
    with closing(_conn()) as conn, conn:
        conn.execute("DELETE FROM profile_answers")
        conn.executemany(
            "INSERT INTO profile_answers VALUES (?, ?, ?)",
            [(k, v, now) for k, v in answers.items() if v.strip()],
        )


# ---------- AI draft ----------


class DraftLink(BaseModel):
    label: str = Field(description="e.g. github, linkedin, web")
    url: str


class DraftItem(BaseModel):
    kind: Literal["experience", "project", "education", "skill", "certificate", "language"]
    title: str
    org: str | None = None
    period: str | None = None
    location: str | None = None
    bullets: list[str] = []
    tags: list[str] = Field(default=[], description="Skills/tools explicitly mentioned, lowercase")


class DraftProfileLLM(BaseModel):
    """What the model returns. IDs are assigned in code; links are a list for Gemini."""

    name: str
    email: str = ""
    phone: str | None = None
    location: str = ""
    links: list[DraftLink] = []
    summary: str
    items: list[DraftItem]
    follow_up_questions: list[str] = Field(
        default=[], description="Up to 5 specific questions about missing details"
    )


class DraftFlag(BaseModel):
    path: str = Field(description="e.g. 'items[0].bullets[1]' or 'summary'")
    text: str
    reason: str


class ProfileDraft(BaseModel):
    profile: Profile
    follow_up_questions: list[str]
    flags: list[DraftFlag]


KIND_PREFIX = {
    "experience": "exp",
    "project": "proj",
    "education": "edu",
    "skill": "skills",
    "certificate": "cert",
    "language": "lang",
}


def _slug(text: str, max_len: int = 30) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_len].strip("-") or "item"


def to_profile(draft: DraftProfileLLM) -> Profile:
    """Assign readable, unique IDs (`exp-data-intern`, `exp-data-intern-b1`)."""
    used: set[str] = set()
    items = []
    for item in draft.items:
        base = f"{KIND_PREFIX[item.kind]}-{_slug(item.title)}"
        item_id, n = base, 2
        while item_id in used:
            item_id, n = f"{base}-{n}", n + 1
        used.add(item_id)
        bullets = [
            Bullet(id=f"{item_id}-b{i}", text=text) for i, text in enumerate(item.bullets, start=1)
        ]
        used.update(b.id for b in bullets)
        items.append(
            ProfileItem(
                id=item_id,
                kind=item.kind,
                title=item.title,
                org=item.org,
                period=item.period,
                location=item.location,
                bullets=bullets,
                tags=item.tags,
            )
        )
    return Profile(
        name=draft.name,
        email=draft.email,
        phone=draft.phone,
        location=draft.location,
        links={link.label: link.url for link in draft.links},
        summary=draft.summary,
        items=items,
    )


def flag_unsupported(profile: Profile, answers: dict[str, str]) -> list[DraftFlag]:
    """Numbers and organisations in the draft that the candidate never wrote."""
    corpus = "\n".join(answers.values())
    known_numbers, lowered = numbers_in(corpus), corpus.lower()
    flags: list[DraftFlag] = []

    def check_numbers(path: str, text: str | None) -> None:
        for n in sorted(numbers_in(text or "") - known_numbers):
            flags.append(DraftFlag(path=path, text=text, reason=f"Number not in your answers: {n}"))

    check_numbers("summary", profile.summary)
    for i, item in enumerate(profile.items):
        if item.org and item.org.lower() not in lowered:
            flags.append(
                DraftFlag(
                    path=f"items[{i}].org",
                    text=item.org,
                    reason=f"Organisation not in your answers: {item.org}",
                )
            )
        check_numbers(f"items[{i}].title", item.title)
        check_numbers(f"items[{i}].period", item.period)
        for j, bullet in enumerate(item.bullets):
            check_numbers(f"items[{i}].bullets[{j}]", bullet.text)
    return flags


def draft_profile(answers: dict[str, str]) -> ProfileDraft:
    titles = {s.id: s.title for s in GUIDED_SECTIONS}
    user = "\n\n".join(
        f"## {titles.get(k, k)}\n{v.strip()}" for k, v in answers.items() if v.strip()
    )
    raw = structured(DraftProfileLLM, system=prompts.PROFILE_DRAFT, user=user, step="profile_draft")
    profile = to_profile(raw)
    return ProfileDraft(
        profile=profile,
        follow_up_questions=raw.follow_up_questions[:5],
        flags=flag_unsupported(profile, answers),
    )
