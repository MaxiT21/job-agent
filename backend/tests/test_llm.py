from types import SimpleNamespace

import pytest

from app import llm
from app.schemas import ClarifyAnswer


def _response(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture
def fake_completion(monkeypatch):
    replies: list[str] = []
    monkeypatch.setattr(llm.litellm, "completion", lambda **kw: _response(replies.pop(0)))
    monkeypatch.setattr(llm.litellm, "completion_cost", lambda **kw: 0.001)
    return replies


def test_structured_parses_and_records_usage(fake_completion):
    fake_completion.append('{"answer": "Postgres"}')

    with llm.track_usage() as calls:
        out = llm.structured(ClarifyAnswer, system="s", user="u", step="extract", model="m")

    assert out == ClarifyAnswer(answer="Postgres")
    assert [(c["step"], c["model"], c["ok"], c["cost_usd"]) for c in calls] == [
        ("extract", "m", True, 0.001)
    ]


def test_structured_retries_invalid_json_once(fake_completion):
    fake_completion.extend(['{"answer": ""}', '{"answer": "ok"}'])

    with llm.track_usage() as calls:
        out = llm.structured(ClarifyAnswer, system="s", user="u", step="extract", model="m")

    assert out.answer == "ok"
    assert [c["ok"] for c in calls] == [False, True]


def test_calls_outside_tracking_are_not_collected(fake_completion):
    fake_completion.extend(['{"answer": "a"}', '{"answer": "b"}'])
    llm.structured(ClarifyAnswer, system="s", user="u", step="x", model="m")

    with llm.track_usage() as calls:
        llm.structured(ClarifyAnswer, system="s", user="u", step="y", model="m")

    assert [c["step"] for c in calls] == ["y"]


def test_nested_tracking_records_in_every_enclosing_block(fake_completion):
    fake_completion.append('{"answer": "a"}')

    with llm.track_usage() as outer, llm.track_usage() as inner:
        llm.structured(ClarifyAnswer, system="s", user="u", step="x", model="m")

    assert [c["step"] for c in inner] == ["x"]
    assert [c["step"] for c in outer] == ["x"]


def test_calls_are_bounded_by_timeout_and_retry_transient_errors(monkeypatch):
    seen = {}

    def completion(**kwargs):
        seen.update(kwargs)
        return _response('{"answer": "ok"}')

    monkeypatch.setattr(llm.litellm, "completion", completion)
    monkeypatch.setattr(llm.litellm, "completion_cost", lambda **kw: 0.0)
    monkeypatch.setattr(llm.settings, "llm_timeout_s", 90)

    llm.structured(ClarifyAnswer, system="s", user="u", step="x", model="m")

    assert seen["timeout"] == 90
    assert seen["num_retries"] >= 1


@pytest.mark.parametrize(("configured", "sent"), [(None, "absent"), (0.2, 0.2)])
def test_temperature_is_only_sent_when_configured(monkeypatch, configured, sent):
    # Gemini 3 can loop at temperature < 1, so by default we let the provider choose.
    seen = {}

    def completion(**kwargs):
        seen.update(kwargs)
        return _response('{"answer": "ok"}')

    monkeypatch.setattr(llm.litellm, "completion", completion)
    monkeypatch.setattr(llm.litellm, "completion_cost", lambda **kw: 0.0)
    monkeypatch.setattr(llm.settings, "llm_temperature", configured)

    llm.structured(ClarifyAnswer, system="s", user="u", step="x", model="m")

    assert seen.get("temperature", "absent") == sent
