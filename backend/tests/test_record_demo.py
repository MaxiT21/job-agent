"""The demo recorder: real runs on the fictional profile, saved for the public demo."""

from __future__ import annotations

import json

import pytest

from app.config import settings
from app.profile import load_profile
from scripts.record_demo import AutoAnswers, RealProfileError, Scenario, record
from tests.fakes import happy_script, match, posting


def scenario(**kw) -> Scenario:
    base = dict(
        id="strong-match",
        title="Strong match",
        description="A backend internship",
        posting_text="We need a Python + SQL intern. Kubernetes is a plus. Barcelona, hybrid.",
    )
    return Scenario(**(base | kw))


def test_recorder_refuses_a_real_profile(tmp_path, fake_llm):
    fake_llm(happy_script())
    settings.profile_path.parent.mkdir(parents=True, exist_ok=True)
    settings.profile_path.write_text(
        (settings.sample_profile_path).read_text().replace("Alex Example", "Real Person")
    )
    load_profile.cache_clear()

    with pytest.raises(RealProfileError):
        record(scenario(), tmp_path)


def test_records_every_pause_until_done(tmp_path, fake_llm):
    fake_llm(happy_script())

    rec = record(scenario(), tmp_path)

    statuses = [s["view"]["status"] for s in rec["steps"]]
    assert statuses == ["waiting", "done"]
    assert rec["steps"][0]["answer"] == {"approved": True}
    assert rec["steps"][-1]["answer"] is None
    assert rec["profile"]["name"] == "Alex Example"
    saved = json.loads((tmp_path / "strong-match.json").read_text())
    assert saved == rec
    assert (tmp_path / "strong-match" / "cv.docx").exists()
    assert (tmp_path / "strong-match" / "cover_letter.docx").exists()
    # paths on the recording machine never leak into the public demo
    assert str(settings.output_dir) not in (tmp_path / "strong-match.json").read_text()


def test_low_fit_and_clarify_are_answered_with_the_scenario_answers(tmp_path, fake_llm):
    fake_llm(
        happy_script(extract=[posting(vague=True), posting()], match=[match("gap", "gap", "gap")])
    )
    answers = AutoAnswers(clarify="A junior Python role", proceed=True)

    rec = record(scenario(id="vague", answers=answers), tmp_path)

    sent = [s["answer"] for s in rec["steps"]]
    assert sent == [{"answer": "A junior Python role"}, {"proceed": True}, {"approved": True}, None]
