import os

from app.config import load_env_files


def test_env_file_keys_reach_process_environment(tmp_path, monkeypatch):
    """LiteLLM reads provider keys from os.environ, so .env values must be exported."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=test-key\n")

    load_env_files([env])

    assert os.environ["GEMINI_API_KEY"] == "test-key"
    monkeypatch.delenv("GEMINI_API_KEY")


def test_real_environment_wins_over_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-shell")
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=from-file\n")

    load_env_files([env])

    assert os.environ["GEMINI_API_KEY"] == "from-shell"
