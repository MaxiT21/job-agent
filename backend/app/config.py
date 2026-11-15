from collections.abc import Iterable
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
# Earlier files win: backend/.env overrides the repo-root .env (shared with docker compose).
ENV_FILES = (BACKEND_DIR / ".env", REPO_DIR / ".env")


def load_env_files(paths: Iterable[Path]) -> None:
    """Export .env values to os.environ so LiteLLM finds provider keys.

    Variables already set in the real environment are never overridden.
    """
    for path in paths:
        if path.exists():
            load_dotenv(path, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # Any LiteLLM model string, e.g. "gpt-4o-mini", "anthropic/<model>", "gemini/<model>".
    # Check https://docs.litellm.ai/docs/providers for current names.
    model: str = "gpt-4o-mini"
    # Optional cheaper/stronger model just for the verifier (defaults to `model`).
    verifier_model: str | None = None

    profile_path: Path = BACKEND_DIR / "data" / "profile.yaml"
    sample_profile_path: Path = BACKEND_DIR / "data" / "profile.sample.yaml"
    output_dir: Path = BACKEND_DIR / "outputs"
    # SQLite file holding run checkpoints and the application tracker.
    database_path: Path = BACKEND_DIR / "outputs" / "job_agent.db"
    log_level: str = "INFO"

    low_fit_threshold: float = 50.0  # below this the agent asks before continuing
    max_verify_retries: int = 2

    cors_origins: list[str] = ["http://localhost:3000"]


load_env_files(ENV_FILES)
settings = Settings()
