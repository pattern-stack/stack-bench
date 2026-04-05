from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    agent_name: str
    model: str
    state: str
    error_message: str | None = None
    exchange_count: int
    total_input_tokens: int
    total_output_tokens: int
    conversation_type: str = "execution"
    project_id: UUID | None = None
    branched_from_id: UUID | None = None
    branched_at_sequence: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
