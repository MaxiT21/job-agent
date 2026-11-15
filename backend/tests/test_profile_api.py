"""Profile builder: guided answers -> AI draft (organise, never add) -> review -> save."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agent.graph import build_graph, get_graph
from app.main import app
from app.profile import load_profile
from app.profile_builder import DraftItem, DraftLink, DraftProfileLLM, draft_profile
from tests.conftest import TEST_PASSWORD

ANSWERS = {
    "basics": "Maria Lopez, maria@example.com, Valencia. github.com/marial",
    "experience": "Data intern at Acme Analytics (Jan 2026 - Jun 2026). Built Power BI dashboards "
    "used by 12 managers and cleaned sales data with SQL.",
    "skills": "SQL, Power BI, Python",
}


def llm_draft(**overrides) -> DraftProfileLLM:
    data = {
        "name": "Maria Lopez",
        "email": "maria@example.com",
        "location": "Valencia",
        "links": [DraftLink(label="github", url="github.com/marial")],
        "summary": "Data intern building dashboards with Power BI and SQL.",
        "items": [
            DraftItem(
                kind="experience",
                title="Data Intern",
                org="Acme Analytics",
                period="Jan 2026 - Jun 2026",
                bullets=[
                    "Built Power BI dashboards used by 12 managers.",
                    "Cleaned sales data with SQL.",
                ],
                tags=["power bi", "sql"],
            ),
            DraftItem(kind="skill", title="Core skills", tags=["sql", "power bi", "python"]),
        ],
        "follow_up_questions": ["What did the dashboards help managers decide?"],
    }
    data.update(overrides)
    return DraftProfileLLM(**data)


@pytest.fixture
def client():
    app.dependency_overrides[get_graph] = build_graph
    c = TestClient(app)
    assert c.post("/auth/login", json={"password": TEST_PASSWORD}).status_code == 204
    yield c
    app.dependency_overrides.clear()


def test_draft_normalizes_ids(fake_llm):
    fake_llm({"profile_draft": [llm_draft()]})

    draft = draft_profile(ANSWERS)

    ids = [(i.id, [b.id for b in i.bullets]) for i in draft.profile.items]
    assert ids == [
        ("exp-data-intern", ["exp-data-intern-b1", "exp-data-intern-b2"]),
        ("skills-core-skills", []),
    ]
    assert draft.profile.links == {"github": "github.com/marial"}
    assert draft.follow_up_questions == ["What did the dashboards help managers decide?"]


def test_draft_flags_number_not_in_answers(fake_llm):
    inflated = llm_draft()
    inflated.items[0].bullets[0] = "Built Power BI dashboards used by 40 managers."
    fake_llm({"profile_draft": [inflated]})

    flags = draft_profile(ANSWERS).flags

    assert [(f.path, f.reason) for f in flags] == [
        ("items[0].bullets[0]", "Number not in your answers: 40")
    ]


def test_draft_flags_organisation_not_in_answers(fake_llm):
    wrong = llm_draft()
    wrong.items[0].org = "Globex"
    fake_llm({"profile_draft": [wrong]})

    flags = draft_profile(ANSWERS).flags

    assert [(f.path, f.reason) for f in flags] == [
        ("items[0].org", "Organisation not in your answers: Globex")
    ]


def test_draft_does_not_flag_facts_from_answers(fake_llm):
    fake_llm({"profile_draft": [llm_draft()]})
    assert draft_profile(ANSWERS).flags == []


def test_draft_endpoint(client, fake_llm):
    fake_llm({"profile_draft": [llm_draft()]})
    r = client.post("/profile/draft", json={"answers": ANSWERS})
    assert r.status_code == 200
    assert r.json()["profile"]["name"] == "Maria Lopez"


def test_save_profile_switches_source_and_agent_uses_it(client, fake_llm):
    fake_llm({"profile_draft": [llm_draft()]})
    draft = client.post("/profile/draft", json={"answers": ANSWERS}).json()
    assert client.get("/profile").json()["source"] == "sample"

    r = client.put("/profile", json=draft["profile"])

    assert r.status_code == 200
    body = client.get("/profile").json()
    assert body["source"] == "custom"
    assert body["profile"]["name"] == "Maria Lopez"
    assert load_profile().name == "Maria Lopez"  # the agent reads the saved profile


def test_put_profile_rejects_duplicate_ids_422(client):
    profile = load_profile().model_dump()
    profile["items"][1]["id"] = profile["items"][0]["id"]
    assert client.put("/profile", json=profile).status_code == 422


def test_answers_roundtrip(client):
    assert client.get("/profile/answers").json() == {}
    assert client.put("/profile/answers", json=ANSWERS).status_code == 204
    assert client.get("/profile/answers").json() == ANSWERS


def test_questions_cover_every_section(client):
    sections = client.get("/profile/questions").json()
    ids = [s["id"] for s in sections]
    assert ids[0] == "basics"
    assert {"experience", "projects", "education", "skills", "languages", "cv_text"} <= set(ids)
    assert all(s["prompt"] and s["hints"] for s in sections)
