"""Settings read from the environment; no secrets live in the repo."""
import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "sqlite:///./app.db"


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_expire_hours: int = 8


def get_settings() -> Settings:
    """Build settings from the current environment (JWT_SECRET, DATABASE_URL)."""
    return Settings(
        database_url=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        jwt_secret=os.environ.get("JWT_SECRET", ""),
    )
