from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReviewCommentResponse(BaseModel):
    id: UUID
    pull_request_id: UUID
    branch_id: UUID
    path: str
    line_key: str
    line_number: int | None = None
    side: str | None = None
    body: str
    author: str
    external_id: int | None = None
    resolved: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
