from collections.abc import Iterable
from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr
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
    # Sampling temperature; unset = provider default (Gemini 3 can loop below 1.0).
    llm_temperature: float | None = None
    llm_timeout_s: float = 120  # per LLM call; a hung provider must not hang the run
    llm_num_retries: int = 2  # LiteLLM retries for transient errors (rate limits, 5xx)
    max_verify_retries: int = 2
    max_clarifications: int = 2  # questions about a vague posting before moving on

    # Single-user auth for the web app. Without APP_PASSWORD every private endpoint returns 503.
    app_password: SecretStr | None = None
    # Signs session cookies; if unset a random one is used and sessions reset on restart.
    session_secret: SecretStr | None = None
    session_days: int = 30
    cookie_secure: bool = False  # set true when the app is served over HTTPS

    cors_origins: list[str] = ["http://localhost:3000"]


load_env_files(ENV_FILES)
settings = Settings()
