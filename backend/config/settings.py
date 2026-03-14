from functools import lru_cache

from pattern_stack.atoms.config.settings import Settings as BaseSettings
from pydantic import Field


class AppSettings(BaseSettings):  # type: ignore[misc]
    APP_NAME: str = Field(default="Stack Bench")
    APP_VERSION: str = Field(default="0.1.0")
    DATABASE_URL: str = Field(default="postgresql+asyncpg://stack-bench:password@localhost:5832/stack-bench")
    WEBHOOK_SECRET: str = Field(default="")
    ANTHROPIC_API_KEY: str = Field(default="")

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
