from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BranchResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    stack_id: UUID
    workspace_id: UUID
    name: str
    position: int
    head_sha: str | None = None
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
