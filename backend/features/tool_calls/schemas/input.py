from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class ToolCallCreate(BaseModel):
    conversation_id: UUID
    tool_call_id: str = PydanticField(..., min_length=1, max_length=200)
    tool_name: str = PydanticField(..., min_length=1, max_length=200)
    arguments: dict[str, Any] | None = None
    request_part_id: UUID | None = None


class ToolCallUpdate(BaseModel):
    result: str | None = None
    error: str | None = None
    duration_ms: int | None = None
    response_part_id: UUID | None = None
