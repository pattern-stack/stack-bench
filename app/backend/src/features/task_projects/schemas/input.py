from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class TaskProjectCreate(BaseModel):
    name: str = PydanticField(..., min_length=1, max_length=500)
    description: str | None = None
    lead_id: UUID | None = None
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str = PydanticField("local", pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None


class TaskProjectUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=500)
    description: str | None = None
    lead_id: UUID | None = None
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str | None = PydanticField(None, pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None
