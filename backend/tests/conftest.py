from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest

from app.config import settings
from app.profile import load_profile
from tests.fakes import FakeLLM


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Never touch the developer's real profile, outputs or database from tests."""
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")
    monkeypatch.setattr(settings, "profile_path", tmp_path / "no-real-profile.yaml")
    load_profile.cache_clear()
    yield settings
    load_profile.cache_clear()


@pytest.fixture
def fake_llm(monkeypatch) -> Callable[..., FakeLLM]:
    """`fake_llm(script)` installs a FakeLLM for every graph node and returns it."""

    def install(script: dict, strict: bool = False) -> FakeLLM:
        fake = FakeLLM(script, strict=strict)
        monkeypatch.setattr("app.agent.nodes.structured", fake)
        return fake

    return install


@pytest.fixture
def thread() -> dict:
    return {"configurable": {"thread_id": str(uuid.uuid4())}}
