from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class MessageCreate(BaseModel):
    conversation_id: UUID
    kind: str = PydanticField(..., min_length=1, max_length=20)
    sequence: int
    run_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class MessageUpdate(BaseModel):
    run_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
