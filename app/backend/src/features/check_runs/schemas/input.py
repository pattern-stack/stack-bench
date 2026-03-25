from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class CheckRunCreate(BaseModel):
    pull_request_id: UUID
    external_id: int
    head_sha: str = PydanticField(..., min_length=1, max_length=40)
    name: str = PydanticField(..., min_length=1, max_length=200)
    status: str = PydanticField(..., max_length=20)
    conclusion: str | None = PydanticField(None, max_length=20)


class CheckRunUpdate(BaseModel):
    head_sha: str | None = PydanticField(None, max_length=40)
    status: str | None = PydanticField(None, max_length=20)
    conclusion: str | None = PydanticField(None, max_length=20)
