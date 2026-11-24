"""Runtime settings, resolved once from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    base_url: str
    admin_username: str
    admin_password: str
    chromium_executable: str | None

    @property
    def is_production(self) -> bool:
        return "mpls7.pages.dev" in self.base_url and "staging" not in self.base_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        base_url=os.getenv("BASE_URL", "http://127.0.0.1:8788").rstrip("/"),
        admin_username=os.getenv("ADMIN_USERNAME", "admin"),
        admin_password=os.getenv("ADMIN_PASSWORD", "qa-admin-pass"),
        chromium_executable=os.getenv("CHROMIUM_EXECUTABLE") or None,
    )
