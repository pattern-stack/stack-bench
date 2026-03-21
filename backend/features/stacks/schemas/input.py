from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class StackCreate(BaseModel):
    project_id: UUID
    name: str = PydanticField(..., min_length=1, max_length=200)
    base_branch_id: UUID | None = None
    trunk: str = PydanticField("main", min_length=1, max_length=200)


class StackUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=200)
    base_branch_id: UUID | None = None
    trunk: str | None = PydanticField(None, min_length=1, max_length=200)
