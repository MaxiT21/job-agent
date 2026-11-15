"""Test doubles: a scripted LLM and canned outputs that are valid against the sample profile."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel

from app.schemas import (
    CoverLetter,
    CVEntry,
    GroundedLine,
    JobPosting,
    MatchResult,
    Requirement,
    RequirementMatch,
    TailoredCV,
    VerificationIssue,
    VerificationResult,
)


class ScriptExhausted(AssertionError):
    pass


class FakeLLM:
    """Replaces `app.llm.structured`. Each step returns its scripted responses in order.

    The last response of a step is repeated if the step is called more times than scripted,
    unless `strict=True`. Exceptions in the script are raised instead of returned.
    """

    def __init__(self, responses: dict[str, list[Any]], strict: bool = False):
        self.responses = {k: list(v) for k, v in responses.items()}
        self.strict = strict
        self.calls: list[tuple[str, str]] = []  # (step, user prompt)
        self.systems: dict[str, list[str]] = defaultdict(list)

    def __call__(self, schema, *, system: str, user: str, step: str, model=None, retries=1):
        self.calls.append((step, user))
        self.systems[step].append(system)
        queue = self.responses.get(step)
        if not queue:
            raise ScriptExhausted(f"No scripted response for step {step!r}")
        item = queue.pop(0) if (len(queue) > 1 or self.strict) else queue[0]
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, schema), f"{step}: scripted {type(item).__name__}, wanted {schema}"
        return item

    def steps(self) -> list[str]:
        return [s for s, _ in self.calls]

    def prompts(self, step: str) -> list[str]:
        return [u for s, u in self.calls if s == step]


# ---------- canned outputs (IDs exist in data/profile.sample.yaml) ----------


def posting(*, vague: bool = False, language: str = "en") -> JobPosting:
    return JobPosting(
        title="Backend Developer Intern",
        company="Acme",
        location="Barcelona",
        seniority="intern",
        language=language,
        requirements=[]
        if vague
        else [
            Requirement(id="r1", text="Python", category="skill", importance="must"),
            Requirement(id="r2", text="SQL", category="skill", importance="must"),
            Requirement(id="r3", text="Kubernetes", category="skill", importance="nice"),
        ],
        is_vague=vague,
        clarifying_question="What stack does the team use?" if vague else None,
    )


def match(*statuses: str) -> MatchResult:
    """One status per requirement r1..rN."""
    evidence = {"met": ["skills-core"], "partial": ["skills-core"], "gap": []}
    return MatchResult(
        matches=[
            RequirementMatch(
                requirement_id=f"r{i}", status=s, evidence_ids=evidence[s], note="judged"
            )
            for i, s in enumerate(statuses, start=1)
        ],
        summary="Fit summary",
    )


def good_cv() -> TailoredCV:
    return TailoredCV(
        summary=GroundedLine(
            text="Computer engineering student building Python backends.",
            evidence_ids=["edu-bsc", "proj-network-monitor"],
        ),
        entries=[
            CVEntry(
                item_id="proj-network-monitor",
                bullets=[
                    GroundedLine(
                        text="Built a FastAPI backend serving device status to a dashboard.",
                        evidence_ids=["proj-network-monitor-b1"],
                    )
                ],
            ),
            CVEntry(
                item_id="exp-consulting",
                bullets=[
                    GroundedLine(
                        text="Validated data with SQL queries and triaged defects in Jira.",
                        evidence_ids=["exp-consulting-b2"],
                    )
                ],
            ),
        ],
        skills=["Python", "FastAPI", "SQL"],
    )


def good_letter() -> CoverLetter:
    return CoverLetter(
        paragraphs=[
            GroundedLine(
                text="I built a FastAPI backend for a home network monitor.",
                evidence_ids=["proj-network-monitor-b1"],
            ),
            GroundedLine(
                text="During my internship I validated data with SQL.",
                evidence_ids=["exp-consulting-b2"],
            ),
        ]
    )


def verify_pass() -> VerificationResult:
    return VerificationResult(passed=True, issues=[])


def verify_fail(
    where: str = "cv.entries[0].bullets[0]", reason: str = "Adds a claim"
) -> VerificationResult:
    return VerificationResult(
        passed=False, issues=[VerificationIssue(where=where, text="some line", reason=reason)]
    )


def happy_script(**overrides: list[BaseModel | Exception]) -> dict[str, list[Any]]:
    script: dict[str, list[Any]] = {
        "extract": [posting()],
        "match": [match("met", "met", "gap")],
        "tailor_cv": [good_cv()],
        "cover_letter": [good_letter()],
        "verify": [verify_pass()],
    }
    script.update(overrides)
    return script
