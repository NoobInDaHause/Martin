from dataclasses import dataclass
import json
from typing import Dict, List


@dataclass
class Settings:
    default_prefixes: List[str]
    guild_prefixes: Dict[str, List[str]]
    global_hex_colour: str
    blacklisted_user_ids: List[int]
    __version__: str

    @classmethod
    def initialize(cls) -> "Settings":
        with open("config.json", "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        return cls(**data)
