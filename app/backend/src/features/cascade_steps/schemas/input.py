from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class CascadeStepCreate(BaseModel):
    cascade_id: UUID
    branch_id: UUID
    pull_request_id: UUID | None = None
    position: int = PydanticField(..., ge=1)
    check_run_external_id: int | None = None
    head_sha: str | None = PydanticField(None, max_length=40)


class CascadeStepUpdate(BaseModel):
    pull_request_id: UUID | None = None
    check_run_external_id: int | None = None
    head_sha: str | None = PydanticField(None, max_length=40)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
