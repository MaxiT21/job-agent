"""HTTP contract of the API (scripted LLM, in-memory checkpoints, temp database)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agent.graph import build_graph, get_graph
from app.main import app
from tests.fakes import happy_script, match

POSTING = {"posting_text": "We need a Python + SQL intern. Kubernetes is a plus."}
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture
def client():
    graph = build_graph()
    app.dependency_overrides[get_graph] = lambda: graph
    yield TestClient(app)
    app.dependency_overrides.clear()


def start(client, body=POSTING) -> dict:
    r = client.post("/runs", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_full_flow_start_approve_download(client, fake_llm):
    fake_llm(happy_script())

    run = start(client)
    assert run["status"] == "waiting"
    assert run["waiting_for"]["type"] == "approve"
    assert run["fit"]["score"] == 80.0  # r1,r2 met (2+2), r3 gap (0 of 1) -> 4/5
    assert run["cv"]["skills"] == ["Python", "FastAPI", "SQL"]
    assert [c["step"] for c in run["usage"]["calls"]] == [
        "extract",
        "match",
        "tailor_cv",
        "cover_letter",
        "verify",
    ]

    r = client.post(f"/runs/{run['run_id']}/resume", json={"value": {"approved": True}})
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["status"] == "done"
    assert done["files"] == {"cv": True, "cover_letter": True}

    for kind in ("cv", "cover_letter"):
        f = client.get(f"/runs/{run['run_id']}/files/{kind}")
        assert f.status_code == 200
        assert f.headers["content-type"] == DOCX
        assert f.content[:2] == b"PK"  # docx is a zip

    apps = client.get("/applications").json()
    assert [a["run_id"] for a in apps] == [run["run_id"]]


def test_start_requires_url_or_text(client):
    assert client.post("/runs", json={}).status_code == 422


def test_resume_wrong_shape_422(client, fake_llm):
    fake_llm(happy_script(match=[match("gap", "gap", "gap")]))
    run = start(client)
    assert run["waiting_for"]["type"] == "low_fit"

    r = client.post(f"/runs/{run['run_id']}/resume", json={"value": {"approved": True}})

    assert r.status_code == 422
    assert "proceed" in r.text
    assert client.get(f"/runs/{run['run_id']}").json()["waiting_for"]["type"] == "low_fit"


def test_resume_without_pending_interrupt_409(client, fake_llm):
    fake_llm(happy_script())
    run = start(client)
    client.post(f"/runs/{run['run_id']}/resume", json={"value": {"approved": True}})

    r = client.post(f"/runs/{run['run_id']}/resume", json={"value": {"approved": True}})
    assert r.status_code == 409


def test_provider_error_then_retry(client, fake_llm):
    fake_llm(
        happy_script(match=[RuntimeError("Gemini 503: overloaded"), match("met", "met", "gap")])
    )

    run = start(client)
    assert run["status"] == "error"
    assert "overloaded" in run["error"]
    assert client.get(f"/runs/{run['run_id']}").json()["status"] == "error"

    r = client.post(f"/runs/{run['run_id']}/retry")
    assert r.status_code == 200
    assert r.json()["status"] == "waiting"
    assert r.json()["error"] is None


def test_retry_without_error_409(client, fake_llm):
    fake_llm(happy_script())
    run = start(client)
    assert client.post(f"/runs/{run['run_id']}/retry").status_code == 409


def test_unknown_run_404(client):
    assert client.get("/runs/nope").status_code == 404
    assert client.post("/runs/nope/resume", json={"value": {"approved": True}}).status_code == 404
    assert client.get("/runs/nope/files/cv").status_code == 404


def test_file_not_ready_404(client, fake_llm):
    fake_llm(happy_script())
    run = start(client)
    assert client.get(f"/runs/{run['run_id']}/files/cv").status_code == 404


def test_update_application_status(client, fake_llm):
    fake_llm(happy_script())
    run = start(client)
    client.post(f"/runs/{run['run_id']}/resume", json={"value": {"approved": True}})

    r = client.patch(f"/applications/{run['run_id']}", json={"status": "applied"})
    assert r.status_code == 200
    assert r.json()["status"] == "applied"
    assert client.patch("/applications/nope", json={"status": "applied"}).status_code == 404
    bad = client.patch(f"/applications/{run['run_id']}", json={"status": "hired!"})
    assert bad.status_code == 422


def test_health_reports_profile_source(client):
    body = client.get("/health").json()
    assert body["ok"] is True
    assert body["profile"] == "sample"
