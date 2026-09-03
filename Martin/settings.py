import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parents[1]
COGS_DATA_PATH = Path(__file__).parents[1] / "cogs_data"


@dataclass
class Settings:
    global_hex_colour: str
    blacklisted_user_ids: List[int]

    @classmethod
    def initialize(cls) -> "Settings":
        with (PROJECT_ROOT / "config.json").open(encoding="utf-8") as config_file:
            data: dict = json.load(config_file)
            data.pop(
                "__version__", None
            )  # versioning moved from config.json to version.txt in v0.0.3
            data.pop("default_prefixes", None)  # Removed in v1.0.0
            data.pop("guild_prefixes", None)  # Removed in v1.0.0
        return cls(**data)
