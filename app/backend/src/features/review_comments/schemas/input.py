from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class ReviewCommentCreate(BaseModel):
    pull_request_id: UUID
    branch_id: UUID
    path: str = PydanticField(..., max_length=500)
    line_key: str = PydanticField(..., max_length=200)
    body: str
    author: str = PydanticField(..., max_length=200)
    line_number: int | None = None
    side: str | None = None


class ReviewCommentUpdate(BaseModel):
    body: str | None = None
    resolved: bool | None = None
