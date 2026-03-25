from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator
from pydantic import Field as PydanticField


class ProjectCreate(BaseModel):
    name: str = PydanticField(..., min_length=1, max_length=200)
    description: str | None = None
    metadata_: dict[str, Any] | None = None
    owner_id: UUID
    local_path: str | None = None
    github_repo: str = PydanticField(..., min_length=1, max_length=500)

    @field_validator("local_path")
    @classmethod
    def validate_local_path_exists(cls, v: str | None) -> str | None:
        """Validate that local_path points to an existing directory (skip if None)."""
        if v is None:
            return v
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Directory does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return v

    @field_validator("github_repo")
    @classmethod
    def validate_github_repo_format(cls, v: str) -> str:
        """Validate github_repo is a valid GitHub URL."""
        if "github.com" not in v:
            raise ValueError("github_repo must be a GitHub URL (must contain github.com)")
        if not v.startswith("https://"):
            raise ValueError("github_repo must be an HTTPS URL (must start with https://)")
        parts = v.split("/")
        if len(parts) < 5 or parts[-2] == "" or parts[-1] == "":
            raise ValueError("github_repo must follow format: https://github.com/user/repo")
        return v


class ProjectUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=200)
    description: str | None = None
    metadata_: dict[str, Any] | None = None
    local_path: str | None = PydanticField(None, min_length=1, max_length=500)
    github_repo: str | None = PydanticField(None, min_length=1, max_length=500)

    @field_validator("local_path")
    @classmethod
    def validate_local_path_exists(cls, v: str | None) -> str | None:
        """Validate that local_path points to an existing directory."""
        if v is None:
            return v
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Directory does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return v

    @field_validator("github_repo")
    @classmethod
    def validate_github_repo_format(cls, v: str | None) -> str | None:
        """Validate github_repo is a valid GitHub URL."""
        if v is None:
            return v
        if "github.com" not in v:
            raise ValueError("github_repo must be a GitHub URL (must contain github.com)")
        if not v.startswith("https://"):
            raise ValueError("github_repo must be an HTTPS URL (must start with https://)")
        parts = v.split("/")
        if len(parts) < 5 or parts[-2] == "" or parts[-1] == "":
            raise ValueError("github_repo must follow format: https://github.com/user/repo")
        return v
