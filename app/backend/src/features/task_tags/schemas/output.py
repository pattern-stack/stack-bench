from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TaskTagResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    name: str
    color: str | None = None
    description: str | None = None
    group: str | None = None
    is_exclusive: bool
    external_id: str | None = None
    external_url: str | None = None
    provider: str
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
