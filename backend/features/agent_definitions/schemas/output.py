from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AgentDefinitionResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    name: str
    role_template_id: UUID
    model_override: str | None = None
    mission: str
    background: str | None = None
    awareness: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentDefinitionSummary(BaseModel):
    id: UUID
    name: str
    is_active: bool

    model_config = {"from_attributes": True}
