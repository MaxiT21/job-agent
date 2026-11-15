"""Deterministic parts of the agent: fit score and evidence checks.

Kept out of the LLM on purpose: numbers you can reproduce and test.
"""

from __future__ import annotations

import re

from app.schemas import (
    CoverLetter,
    GroundedLine,
    JobPosting,
    Profile,
    RequirementMatch,
    TailoredCV,
    VerificationIssue,
)

IMPORTANCE_WEIGHT = {"must": 2.0, "nice": 1.0}
STATUS_VALUE = {"met": 1.0, "partial": 0.5, "gap": 0.0}

# Kinds that can appear as a CV entry (skills/languages go in the skills line instead).
ENTRY_KINDS = {"experience", "project", "education", "certificate"}
# A bullet must not borrow evidence from a different item of these kinds (misattribution).
EXCLUSIVE_KINDS = {"experience", "project"}

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def fit_score(posting: JobPosting, matches: list[RequirementMatch]) -> float:
    """Weighted % of requirements covered. Must-haves count double."""
    by_id = {m.requirement_id: m for m in matches}
    total = earned = 0.0
    for req in posting.requirements:
        w = IMPORTANCE_WEIGHT[req.importance]
        total += w
        m = by_id.get(req.id)
        if m:
            earned += w * STATUS_VALUE[m.status]
    return round(100 * earned / total, 1) if total else 0.0


def numbers_in(text: str) -> set[str]:
    """Numbers normalised without thousands/decimal separators: '1,200' == '1200'."""
    return {re.sub(r"[.,]", "", n) for n in _NUMBER.findall(text)}


def check_evidence_ids(
    profile: Profile,
    cv: TailoredCV,
    letter: CoverLetter | None,
    posting_text: str = "",
) -> list[VerificationIssue]:
    """Layer 1 of verification. Free, deterministic, and run before the LLM fact-check.

    - every line cites at least one real profile ID;
    - CV entries are real, unique, entry-type items;
    - each entry bullet cites its own item and never another job/project;
    - every number in a line appears in the evidence it cites (the cover letter may also
      quote numbers from the posting itself);
    - every listed skill exists in the profile.
    """
    valid = profile.evidence_ids()
    issues: list[VerificationIssue] = []

    def flag(where: str, text: str, reason: str) -> None:
        issues.append(VerificationIssue(where=where, text=text, reason=reason))

    def check_line(where: str, line: GroundedLine, extra_text: str = "") -> None:
        if not line.evidence_ids:
            flag(where, line.text, "No evidence cited")
            return
        if unknown := [i for i in line.evidence_ids if i not in valid]:
            flag(where, line.text, f"Unknown evidence ids: {unknown}")
            return
        evidence = " ".join(profile.evidence_text(i) for i in line.evidence_ids)
        allowed = numbers_in(evidence) | numbers_in(extra_text)
        for n in sorted(numbers_in(line.text) - allowed):
            flag(where, line.text, f"Number not in evidence: {n}")

    check_line("cv.summary", cv.summary)

    seen: set[str] = set()
    for ei, entry in enumerate(cv.entries):
        where = f"cv.entries[{ei}]"
        item = profile.item(entry.item_id)
        if item is None:
            flag(where, entry.item_id, "Unknown item")
            continue
        if item.kind not in ENTRY_KINDS:
            flag(where, entry.item_id, f"A {item.kind} item cannot be a CV entry")
            continue
        if entry.item_id in seen:
            flag(where, entry.item_id, "Duplicate entry")
            continue
        seen.add(entry.item_id)

        for bi, line in enumerate(entry.bullets):
            bwhere = f"{where}.bullets[{bi}]"
            before = len(issues)
            check_line(bwhere, line)
            if len(issues) > before:
                continue
            owners = [profile.owner(i) for i in line.evidence_ids]
            if not any(o and o.id == item.id for o in owners):
                flag(bwhere, line.text, f"Bullet does not cite its own item ({item.id})")
            foreign = sorted(
                {o.id for o in owners if o and o.id != item.id and o.kind in EXCLUSIVE_KINDS}
            )
            if foreign:
                flag(bwhere, line.text, f"Evidence belongs to a different item: {foreign}")

    profile_skills = {
        s.lower()
        for item in profile.items
        for s in [*item.tags, item.title]
        if item.kind == "skill"
    } | {t.lower() for item in profile.items for t in item.tags}
    for s in cv.skills:
        if s.strip().lower() not in profile_skills:
            flag("cv.skills", s, "Skill not in profile")

    if letter:
        for pi, line in enumerate(letter.paragraphs):
            check_line(f"cover_letter[{pi}]", line, extra_text=posting_text)
    return issues
