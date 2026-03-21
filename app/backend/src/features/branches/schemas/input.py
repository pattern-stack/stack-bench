from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class BranchCreate(BaseModel):
    stack_id: UUID
    workspace_id: UUID
    name: str = PydanticField(..., min_length=1, max_length=500)
    position: int = PydanticField(..., ge=1)
    head_sha: str | None = PydanticField(None, max_length=40)


class BranchUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=500)
    position: int | None = PydanticField(None, ge=1)
    head_sha: str | None = PydanticField(None, max_length=40)
    workspace_id: UUID | None = None
