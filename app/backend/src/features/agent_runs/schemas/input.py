from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class AgentRunCreate(BaseModel):
    job_id: UUID
    phase: str = PydanticField(..., min_length=1, max_length=50)
    runner_type: str = PydanticField(..., min_length=1, max_length=50)
    model_used: str | None = None
    attempt: int = 1


class AgentRunUpdate(BaseModel):
    model_used: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    artifact: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
