from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class TaskRelationCreate(BaseModel):
    source_task_id: UUID
    target_task_id: UUID
    relation_type: str = PydanticField(..., pattern="^(parent_of|blocks|relates_to|duplicates)$")
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str = PydanticField("local", pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None


class TaskRelationUpdate(BaseModel):
    relation_type: str | None = PydanticField(None, pattern="^(parent_of|blocks|relates_to|duplicates)$")
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str | None = PydanticField(None, pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None
