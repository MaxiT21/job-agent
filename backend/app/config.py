from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Any LiteLLM model string, e.g. "gpt-4o-mini", "anthropic/<model>", "gemini/<model>".
    # Check https://docs.litellm.ai/docs/providers for current names.
    model: str = "gpt-4o-mini"
    # Optional cheaper/stronger model just for the verifier (defaults to `model`).
    verifier_model: str | None = None

    profile_path: Path = BACKEND_DIR / "data" / "profile.yaml"
    sample_profile_path: Path = BACKEND_DIR / "data" / "profile.sample.yaml"
    output_dir: Path = BACKEND_DIR / "outputs"

    low_fit_threshold: float = 50.0  # below this the agent asks before continuing
    max_verify_retries: int = 2

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
