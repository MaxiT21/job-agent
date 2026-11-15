from functools import lru_cache

import yaml

from app.config import settings
from app.schemas import Profile


@lru_cache
def load_profile() -> Profile:
    """Load the real profile if present (gitignored), otherwise the fictional sample."""
    path = settings.profile_path if settings.profile_path.exists() else settings.sample_profile_path
    with open(path, encoding="utf-8") as f:
        return Profile.model_validate(yaml.safe_load(f))
