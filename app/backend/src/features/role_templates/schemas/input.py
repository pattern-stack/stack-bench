from typing import Any

from pydantic import BaseModel
from pydantic import Field as PydanticField


class RoleTemplateCreate(BaseModel):
    name: str = PydanticField(..., min_length=1, max_length=100)
    source: str = "custom"
    archetype: str | None = None
    default_model: str | None = None
    persona: dict[str, Any] = PydanticField(default_factory=dict)
    judgments: list[Any] = PydanticField(default_factory=list)
    responsibilities: list[Any] = PydanticField(default_factory=list)
    description: str | None = None
    is_active: bool = True


class RoleTemplateUpdate(BaseModel):
    name: str | None = None
    source: str | None = None
    archetype: str | None = None
    default_model: str | None = None
    persona: dict[str, Any] | None = None
    judgments: list[Any] | None = None
    responsibilities: list[Any] | None = None
    description: str | None = None
    is_active: bool | None = None
