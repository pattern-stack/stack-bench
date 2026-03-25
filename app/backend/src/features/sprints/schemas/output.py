from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SprintResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    name: str
    number: int | None = None
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    state: str
    project_id: UUID | None = None
    external_id: str | None = None
    external_url: str | None = None
    provider: str
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
