from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CheckRunResponse(BaseModel):
    id: UUID
    pull_request_id: UUID
    external_id: int
    head_sha: str
    name: str
    status: str
    conclusion: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
