from functools import lru_cache
from pathlib import Path

from pattern_stack.atoms.config.settings import Settings as BaseSettings
from pydantic import Field

# Project root: config/ -> backend/ -> app/ -> root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class AppSettings(BaseSettings):
    APP_NAME: str = Field(default="Stack Bench")
    APP_VERSION: str = Field(default="0.1.0")
    DATABASE_URL: str = Field(default="postgresql+asyncpg://stack-bench:password@localhost:5932/stack-bench")
    WEBHOOK_SECRET: str = Field(default="")
    ANTHROPIC_API_KEY: str = Field(default="")

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
