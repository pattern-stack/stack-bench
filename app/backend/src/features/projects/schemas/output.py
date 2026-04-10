from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProjectResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    name: str
    description: str | None = None
    metadata_: dict[str, Any] | None = None
    state: str
    created_at: datetime
    updated_at: datetime
    owner_id: UUID
    local_path: str | None = None
    github_repo: str

    model_config = {"from_attributes": True}
