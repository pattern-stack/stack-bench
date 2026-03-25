from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TaskCommentResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    body: str
    edited_at: datetime | None = None
    task_id: UUID
    author_id: UUID | None = None
    parent_id: UUID | None = None
    external_id: str | None = None
    external_url: str | None = None
    provider: str
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
