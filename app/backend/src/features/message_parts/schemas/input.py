from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class MessagePartCreate(BaseModel):
    message_id: UUID
    position: int
    part_type: str = PydanticField(..., min_length=1, max_length=50)
    content: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None


class MessagePartUpdate(BaseModel):
    content: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
