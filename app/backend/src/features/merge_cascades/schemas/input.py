from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class MergeCascadeCreate(BaseModel):
    stack_id: UUID
    triggered_by: str = PydanticField(..., min_length=1, max_length=200)
    current_position: int = 0


class MergeCascadeUpdate(BaseModel):
    current_position: int | None = None
    error: str | None = None
