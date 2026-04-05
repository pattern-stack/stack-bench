from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    state: str
    task_id: UUID | None = None
    repo_url: str
    repo_branch: str
    issue_number: int | None = None
    issue_title: str | None = None
    current_phase: str | None = None
    error_message: str | None = None
    artifacts: dict[str, Any]
    gate_decisions: list[Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
