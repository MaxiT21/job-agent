"""Tests that run without any LLM call."""
from app.profile import load_profile
from app.schemas import (
    CVEntry,
    GroundedLine,
    JobPosting,
    Requirement,
    RequirementMatch,
    TailoredCV,
)
from app.scoring import check_evidence_ids, fit_score


def _posting() -> JobPosting:
    return JobPosting(
        title="AI Developer Intern",
        company="Acme",
        requirements=[
            Requirement(id="r1", text="Python", category="skill", importance="must"),
            Requirement(id="r2", text="Kubernetes", category="skill", importance="nice"),
        ],
    )


def test_sample_profile_loads():
    p = load_profile()
    assert "exp-consulting-b1" in p.evidence_ids()


def test_fit_score_weights_must_haves():
    matches = [
        RequirementMatch(requirement_id="r1", status="met", evidence_ids=["skills-core"], note=""),
        RequirementMatch(requirement_id="r2", status="gap", note=""),
    ]
    assert fit_score(_posting(), matches) == 66.7  # 2 of 3 weighted points


def test_verifier_catches_invented_evidence_and_skills():
    cv = TailoredCV(
        summary=GroundedLine(text="Backend dev", evidence_ids=["skills-core"]),
        entries=[
            CVEntry(
                item_id="proj-network-monitor",
                bullets=[
                    GroundedLine(text="Real bullet", evidence_ids=["proj-network-monitor-b1"]),
                    GroundedLine(text="Led a team of 10", evidence_ids=["made-up-id"]),
                    GroundedLine(text="No evidence", evidence_ids=[]),
                ],
            )
        ],
        skills=["Python", "Kubernetes"],
    )
    issues = check_evidence_ids(load_profile(), cv, None)
    reasons = " | ".join(i.reason for i in issues)
    assert "Unknown evidence ids" in reasons
    assert "No evidence cited" in reasons
    assert any(i.text == "Kubernetes" for i in issues)
    assert not any(i.text == "Python" for i in issues)


def test_graph_compiles():
    from app.agent.graph import graph

    assert "verify" in graph.get_graph().nodes
