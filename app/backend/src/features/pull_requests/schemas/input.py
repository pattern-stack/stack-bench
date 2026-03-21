from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class PullRequestCreate(BaseModel):
    branch_id: UUID
    title: str = PydanticField(..., min_length=1, max_length=500)
    description: str | None = None
    review_notes: str | None = None
    external_id: int | None = None
    external_url: str | None = PydanticField(None, max_length=500)


class PullRequestUpdate(BaseModel):
    title: str | None = PydanticField(None, min_length=1, max_length=500)
    description: str | None = None
    review_notes: str | None = None
    external_id: int | None = None
    external_url: str | None = PydanticField(None, max_length=500)
