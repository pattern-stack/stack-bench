from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    conversation_id: UUID
    kind: str
    sequence: int
    run_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
