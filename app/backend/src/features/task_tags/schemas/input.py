from datetime import datetime

from pydantic import BaseModel
from pydantic import Field as PydanticField


class TaskTagCreate(BaseModel):
    name: str = PydanticField(..., min_length=1, max_length=100)
    color: str | None = PydanticField(None, max_length=7)
    description: str | None = None
    group: str | None = PydanticField(None, max_length=100)
    is_exclusive: bool = False
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str = PydanticField("local", pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None


class TaskTagUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=100)
    color: str | None = PydanticField(None, max_length=7)
    description: str | None = None
    group: str | None = PydanticField(None, max_length=100)
    is_exclusive: bool | None = None
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str | None = PydanticField(None, pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None
