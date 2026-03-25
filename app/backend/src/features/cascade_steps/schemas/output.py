from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CascadeStepResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    cascade_id: UUID
    branch_id: UUID
    pull_request_id: UUID | None = None
    position: int
    check_run_external_id: int | None = None
    head_sha: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
