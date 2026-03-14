from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class AgentDefinitionCreate(BaseModel):
    name: str = PydanticField(..., min_length=1, max_length=100)
    role_template_id: UUID
    model_override: str | None = None
    mission: str = PydanticField(..., min_length=1)
    background: str | None = None
    awareness: dict[str, Any] = PydanticField(default_factory=dict)
    is_active: bool = True


class AgentDefinitionUpdate(BaseModel):
    name: str | None = None
    role_template_id: UUID | None = None
    model_override: str | None = None
    mission: str | None = None
    background: str | None = None
    awareness: dict[str, Any] | None = None
    is_active: bool | None = None
