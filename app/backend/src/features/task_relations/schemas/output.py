from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TaskRelationResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    source_task_id: UUID
    target_task_id: UUID
    relation_type: str
    external_id: str | None = None
    external_url: str | None = None
    provider: str
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
