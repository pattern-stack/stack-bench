from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TaskProjectResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    name: str
    description: str | None = None
    lead_id: UUID | None = None
    state: str
    external_id: str | None = None
    external_url: str | None = None
    provider: str
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
