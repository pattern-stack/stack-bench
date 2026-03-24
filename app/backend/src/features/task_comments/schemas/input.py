from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class TaskCommentCreate(BaseModel):
    body: str = PydanticField(..., min_length=1)
    task_id: UUID = PydanticField(...)
    author_id: UUID | None = None
    parent_id: UUID | None = None
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str = PydanticField("local", pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None


class TaskCommentUpdate(BaseModel):
    body: str | None = PydanticField(None, min_length=1)
    edited_at: datetime | None = None
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str | None = PydanticField(None, pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None
