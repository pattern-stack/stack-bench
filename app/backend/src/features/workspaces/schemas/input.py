from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class WorkspaceCreate(BaseModel):
    project_id: UUID
    name: str = PydanticField(..., min_length=1, max_length=200)
    repo_url: str = PydanticField(..., min_length=1, max_length=500)
    provider: Literal["github", "gitlab", "bitbucket"]
    default_branch: str = PydanticField("main", min_length=1, max_length=200)
    local_path: str | None = None
    metadata_: dict[str, Any] | None = None
    is_active: bool = True


class WorkspaceUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=200)
    repo_url: str | None = PydanticField(None, min_length=1, max_length=500)
    provider: Literal["github", "gitlab", "bitbucket"] | None = None
    default_branch: str | None = PydanticField(None, min_length=1, max_length=200)
    local_path: str | None = None
    metadata_: dict[str, Any] | None = None
    is_active: bool | None = None
