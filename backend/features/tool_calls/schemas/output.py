from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ToolCallResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    conversation_id: UUID
    tool_call_id: str
    tool_name: str
    state: str
    arguments: dict[str, Any] | None = None
    result: str | None = None
    error: str | None = None
    duration_ms: int | None = None
    request_part_id: UUID | None = None
    response_part_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
