from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProjectResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    name: str
    description: str | None = None
    metadata_: dict[str, Any]
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
