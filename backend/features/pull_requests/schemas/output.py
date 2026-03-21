from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PullRequestResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    branch_id: UUID
    external_id: int | None = None
    external_url: str | None = None
    title: str
    description: str | None = None
    review_notes: str | None = None
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
