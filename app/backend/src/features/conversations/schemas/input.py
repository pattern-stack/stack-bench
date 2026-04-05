from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class ConversationCreate(BaseModel):
    agent_name: str = PydanticField(..., min_length=1, max_length=100)
    model: str | None = None
    project_id: UUID | None = None
    metadata_: dict[str, Any] | None = None
    agent_config: dict[str, Any] | None = None
    conversation_type: str | None = None
    branched_from_id: UUID | None = None
    branched_at_sequence: int | None = None


class ConversationUpdate(BaseModel):
    error_message: str | None = None
    exchange_count: int | None = None
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
