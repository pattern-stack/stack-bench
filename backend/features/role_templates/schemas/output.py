from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class RoleTemplateResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    name: str
    source: str
    archetype: str | None = None
    default_model: str | None = None
    persona: dict[str, Any]
    judgments: list[Any]
    responsibilities: list[Any]
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleTemplateSummary(BaseModel):
    id: UUID
    name: str
    archetype: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}
