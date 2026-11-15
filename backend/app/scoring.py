"""Deterministic parts of the agent: fit score and evidence checks.

Kept out of the LLM on purpose: numbers you can reproduce and test.
"""

from app.schemas import (
    CoverLetter,
    JobPosting,
    Profile,
    RequirementMatch,
    TailoredCV,
    VerificationIssue,
)

IMPORTANCE_WEIGHT = {"must": 2.0, "nice": 1.0}
STATUS_VALUE = {"met": 1.0, "partial": 0.5, "gap": 0.0}


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


def check_evidence_ids(
    profile: Profile, cv: TailoredCV, letter: CoverLetter | None
) -> list[VerificationIssue]:
    """Layer 1 of verification: every line cites at least one real profile ID."""
    valid = profile.evidence_ids()
    issues: list[VerificationIssue] = []

    def check(where: str, text: str, ids: list[str]) -> None:
        if not ids:
            issues.append(VerificationIssue(where=where, text=text, reason="No evidence cited"))
        unknown = [i for i in ids if i not in valid]
        if unknown:
            issues.append(
                VerificationIssue(where=where, text=text, reason=f"Unknown evidence ids: {unknown}")
            )

    check("cv.summary", cv.summary.text, cv.summary.evidence_ids)
    for ei, entry in enumerate(cv.entries):
        if entry.item_id not in valid:
            issues.append(
                VerificationIssue(
                    where=f"cv.entries[{ei}]", text=entry.item_id, reason="Unknown item"
                )
            )
        for bi, line in enumerate(entry.bullets):
            check(f"cv.entries[{ei}].bullets[{bi}]", line.text, line.evidence_ids)

    profile_skills = {
        s.lower()
        for item in profile.items
        for s in [*item.tags, item.title]
        if item.kind == "skill"
    } | {t.lower() for item in profile.items for t in item.tags}
    for s in cv.skills:
        if s.lower() not in profile_skills:
            issues.append(
                VerificationIssue(where="cv.skills", text=s, reason="Skill not in profile")
            )

    if letter:
        for pi, line in enumerate(letter.paragraphs):
            check(f"cover_letter[{pi}]", line.text, line.evidence_ids)
    return issues
