from functools import lru_cache
from pathlib import Path
from typing import Literal

from pattern_stack.atoms.config.settings import Settings as BaseSettings
from pydantic import Field

# Project root: config/ → src/ → backend/ → app/ → root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class AppSettings(BaseSettings):
    APP_NAME: str = Field(default="Stack Bench")
    APP_VERSION: str = Field(default="0.1.0")
    DATABASE_URL: str = Field(default="postgresql+asyncpg://stack-bench:password@localhost:5932/stack-bench")
    WEBHOOK_SECRET: str = Field(default="")
    ANTHROPIC_API_KEY: str = Field(default="")
    GITHUB_TOKEN: str = Field(default="")

    # Auth
    JWT_SECRET: str = Field(default="change-me-in-production")
    ENCRYPTION_KEY: str = Field(default="")  # Fernet key for Connection config encryption

    # Frontend URL (for OAuth redirects)
    FRONTEND_URL: str = Field(default="http://localhost:3500")

    # GitHub App OAuth
    GITHUB_APP_ID: str = Field(default="3169724")
    GITHUB_APP_SLUG: str = Field(default="stack-bench")  # Override via env if different
    GITHUB_CLIENT_ID: str = Field(default="Iv23lixxrPIqZQvr3BlX")
    GITHUB_CLIENT_SECRET: str = Field(default="")  # Required for OAuth
    GITHUB_APP_PRIVATE_KEY: str = Field(default="")  # For installation tokens (Phase 4)

    # Event & Job subsystem settings
    EVENT_BACKEND: str = Field(default="memory")  # "memory" or "database"
    BROADCAST_BACKEND: Literal["memory", "redis", "noop"] = Field(default="memory")
    JOB_BACKEND: str = Field(default="memory")  # "memory" or "database"
    JOB_MAX_CONCURRENT: int = Field(default=5)
    JOB_POLL_INTERVAL: float = Field(default=1.0)

    # Ephemeral clone settings
    CLONE_BASE_DIR: str = Field(default="/tmp/stack-bench-clones")
    CLONE_MAX_CONCURRENT: int = Field(default=5)
    CLONE_TTL_SECONDS: int = Field(default=3600)

    # GCP Workspace provisioning
    GCP_PROJECT_ID: str = Field(default="stack-bench")
    GCP_REGION: str = Field(default="northamerica-northeast2")
    GCP_WORKSPACE_IMAGE: str = Field(
        default="northamerica-northeast2-docker.pkg.dev/stack-bench/workspace/workspace-server:latest"
    )
    GCP_SERVICE_ACCOUNT_EMAIL: str = Field(default="")

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
