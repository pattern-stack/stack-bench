from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TaskResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    title: str
    description: str | None = None
    priority: str
    issue_type: str
    work_phase: str | None = None
    status_category: str
    state: str
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    sprint_id: UUID | None = None
    external_id: str | None = None
    external_url: str | None = None
    provider: str
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
