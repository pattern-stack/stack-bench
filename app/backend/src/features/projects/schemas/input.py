from typing import Any

from pydantic import BaseModel
from pydantic import Field as PydanticField


class ProjectCreate(BaseModel):
    name: str = PydanticField(..., min_length=1, max_length=200)
    description: str | None = None
    metadata_: dict[str, Any] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=200)
    description: str | None = None
    metadata_: dict[str, Any] | None = None
