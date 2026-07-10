from __future__ import annotations

import json
from pathlib import Path

from manyu.schemas import ManyuProfile


DEFAULT_PROFILE_PATH = Path("config/default_profile.json")


def load_profile(path: str | Path = DEFAULT_PROFILE_PATH) -> ManyuProfile:
    profile_path = Path(path)
    with profile_path.open("r", encoding="utf-8") as f:
        return ManyuProfile.model_validate(json.load(f))
