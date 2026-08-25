import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class Settings:
    default_prefixes: List[str]
    guild_prefixes: Dict[str, List[str]]
    global_hex_colour: str
    blacklisted_user_ids: List[int]

    @classmethod
    def initialize(cls) -> "Settings":
        project_root = Path(__file__).parents[1]
        with (project_root / "config.json").open(encoding="utf-8") as config_file:
            data: dict = json.load(config_file)
            data.pop(
                "__version__", None
            )  # versioning moved from config.json to version.txt [v0.0.2a]
        return cls(**data)

    @staticmethod
    def version() -> str:
        project_root = Path(__file__).parents[1]
        return (project_root / "version.txt").read_text(encoding="utf-8").strip()
