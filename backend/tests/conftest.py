from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from pydantic import SecretStr

from app import auth
from app.config import settings
from app.profile import load_profile
from tests.fakes import FakeLLM

TEST_PASSWORD = "test-password"


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Never touch the developer's real profile, outputs or database from tests."""
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")
    monkeypatch.setattr(settings, "profile_path", tmp_path / "no-real-profile.yaml")
    monkeypatch.setattr(settings, "database_path", tmp_path / "test.db")
    for name in ("model", "verifier_model"):  # restored after tests that switch models
        monkeypatch.setattr(settings, name, getattr(settings, name))
    monkeypatch.setattr(settings, "app_password", SecretStr(TEST_PASSWORD))
    monkeypatch.setattr(settings, "session_secret", SecretStr("test-secret-" * 4))
    auth.reset_throttle()
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
