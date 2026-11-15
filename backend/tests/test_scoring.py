"""Deterministic scoring and layer-1 verification (no LLM)."""

import pytest
from pydantic import ValidationError

from app.profile import load_profile
from app.schemas import (
    CoverLetter,
    CVEntry,
    GroundedLine,
    JobPosting,
    Profile,
    Requirement,
    RequirementMatch,
    TailoredCV,
)
from app.scoring import check_evidence_ids, fit_score
from tests.fakes import good_cv, good_letter


def _posting() -> JobPosting:
    return JobPosting(
        title="AI Developer Intern",
        company="Acme",
        requirements=[
            Requirement(id="r1", text="Python", category="skill", importance="must"),
            Requirement(id="r2", text="Kubernetes", category="skill", importance="nice"),
        ],
    )


def _cv(*entries: CVEntry, skills: list[str] | None = None) -> TailoredCV:
    return TailoredCV(
        summary=GroundedLine(text="Backend developer.", evidence_ids=["skills-core"]),
        entries=list(entries),
        skills=skills or [],
    )


def _line(text: str, *ids: str) -> GroundedLine:
    return GroundedLine(text=text, evidence_ids=list(ids))


def _reasons(issues) -> str:
    return " | ".join(i.reason for i in issues)


# ---------- fit score ----------


def test_fit_score_weights_must_haves():
    matches = [
        RequirementMatch(requirement_id="r1", status="met", evidence_ids=["skills-core"], note=""),
        RequirementMatch(requirement_id="r2", status="gap", note=""),
    ]
    assert fit_score(_posting(), matches) == 66.7  # 2 of 3 weighted points


# ---------- profile integrity ----------


def test_profile_rejects_duplicate_ids():
    data = {
        "name": "A",
        "email": "a@example.com",
        "location": "X",
        "summary": "S",
        "items": [
            {"id": "p1", "kind": "project", "title": "P", "bullets": [{"id": "dup", "text": "a"}]},
            {"id": "dup", "kind": "project", "title": "Q"},
        ],
    }
    with pytest.raises(ValidationError, match="dup"):
        Profile.model_validate(data)


# ---------- layer-1 verification ----------


def test_valid_cv_and_letter_have_no_issues():
    assert check_evidence_ids(load_profile(), good_cv(), good_letter()) == []


def test_verifier_catches_invented_evidence_and_skills():
    cv = _cv(
        CVEntry(
            item_id="proj-network-monitor",
            bullets=[
                _line("Real bullet", "proj-network-monitor-b1"),
                _line("Led a team", "proj-network-monitor", "made-up-id"),
                _line("No evidence"),
            ],
        ),
        skills=["Python", "Kubernetes"],
    )
    issues = check_evidence_ids(load_profile(), cv, None)
    reasons = _reasons(issues)
    assert "Unknown evidence ids" in reasons
    assert "No evidence cited" in reasons
    assert any(i.text == "Kubernetes" for i in issues)
    assert not any(i.text == "Python" for i in issues)


def test_bullet_citing_other_item_is_flagged():
    # A project's work presented under the internship is a misattribution.
    cv = _cv(
        CVEntry(
            item_id="exp-consulting",
            bullets=[
                _line("Built a FastAPI backend.", "exp-consulting", "proj-network-monitor-b1")
            ],
        )
    )
    issues = check_evidence_ids(load_profile(), cv, None)
    assert [i.where for i in issues] == ["cv.entries[0].bullets[0]"]
    assert "different item" in issues[0].reason


def test_bullet_without_own_item_evidence_is_flagged():
    cv = _cv(CVEntry(item_id="exp-consulting", bullets=[_line("Used SQL.", "skills-core")]))
    issues = check_evidence_ids(load_profile(), cv, None)
    assert [i.where for i in issues] == ["cv.entries[0].bullets[0]"]
    assert "own item" in issues[0].reason


def test_skill_entry_is_rejected():
    cv = _cv(CVEntry(item_id="skills-core", bullets=[]))
    issues = check_evidence_ids(load_profile(), cv, None)
    assert [i.where for i in issues] == ["cv.entries[0]"]


def test_duplicate_entry_is_flagged():
    entry = CVEntry(item_id="edu-bsc", bullets=[])
    issues = check_evidence_ids(load_profile(), _cv(entry, entry), None)
    assert [i.where for i in issues] == ["cv.entries[1]"]
    assert "Duplicate" in issues[0].reason


def test_unsupported_number_is_flagged():
    cv = _cv(
        CVEntry(
            item_id="exp-consulting",
            bullets=[_line("Ran 10 test suites a day.", "exp-consulting-b1")],
        )
    )
    issues = check_evidence_ids(load_profile(), cv, None)
    assert [i.reason for i in issues] == ["Number not in evidence: 10"]


def _numbers_profile() -> Profile:
    return Profile.model_validate(
        {
            "name": "A",
            "email": "a@example.com",
            "location": "X",
            "summary": "S",
            "items": [
                {
                    "id": "job",
                    "kind": "experience",
                    "title": "QA Engineer",
                    "period": "2024 - 2025",
                    "bullets": [
                        {"id": "job-b1", "text": "Cut regression time by 30% on 1,200 tests."}
                    ],
                }
            ],
        }
    )


def test_numbers_from_evidence_pass():
    cv = TailoredCV(
        summary=_line("QA engineer since 2024.", "job"),
        entries=[
            CVEntry(
                item_id="job",
                bullets=[_line("Reduced regression time 30% across 1200 tests.", "job-b1")],
            )
        ],
        skills=[],
    )
    assert check_evidence_ids(_numbers_profile(), cv, None) == []


def test_letter_may_quote_numbers_from_the_posting():
    letter = CoverLetter(
        paragraphs=[_line("Your team of 40 engineers needs QA.", "job-b1")],
    )
    cv = TailoredCV(summary=_line("QA engineer.", "job"), entries=[], skills=[])
    profile = _numbers_profile()

    assert check_evidence_ids(profile, cv, letter, posting_text="A team of 40 engineers") == []
    assert _reasons(check_evidence_ids(profile, cv, letter)) == "Number not in evidence: 40"
