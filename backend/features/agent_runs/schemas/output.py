from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AgentRunResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    state: str
    job_id: UUID
    phase: str
    runner_type: str
    model_used: str | None = None
    input_tokens: int
    output_tokens: int
    artifact: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    attempt: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
