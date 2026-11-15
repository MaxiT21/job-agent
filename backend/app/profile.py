import os
import tempfile
from functools import lru_cache
from typing import Literal

import yaml

from app.config import settings
from app.schemas import Profile


@lru_cache
def load_profile() -> Profile:
    """Load the real profile if present (gitignored), otherwise the fictional sample."""
    path = settings.profile_path if settings.profile_path.exists() else settings.sample_profile_path
    with open(path, encoding="utf-8") as f:
        return Profile.model_validate(yaml.safe_load(f))


def profile_source() -> Literal["custom", "sample"]:
    return "custom" if settings.profile_path.exists() else "sample"


def save_profile(profile: Profile) -> None:
    """Write the real profile atomically and make the agent pick it up immediately."""
    path = settings.profile_path
    path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json", exclude_none=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".profile-", suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("# Your profile. Edited from the web app's profile builder (or by hand).\n")
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=100)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
    load_profile.cache_clear()
