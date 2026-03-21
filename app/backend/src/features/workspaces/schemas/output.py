from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class WorkspaceResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    repo_url: str
    provider: str
    default_branch: str
    local_path: str | None = None
    metadata_: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
