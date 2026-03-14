from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class MessagePartResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    message_id: UUID
    position: int
    part_type: str
    content: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
