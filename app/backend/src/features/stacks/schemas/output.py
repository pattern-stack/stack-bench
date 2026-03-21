from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StackResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    project_id: UUID
    name: str
    base_branch_id: UUID | None = None
    trunk: str
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
