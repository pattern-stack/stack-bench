from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MergeCascadeResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    stack_id: UUID
    triggered_by: str
    current_position: int
    error: str | None = None
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
