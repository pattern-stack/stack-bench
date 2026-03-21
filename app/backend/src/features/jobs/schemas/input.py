from typing import Any

from pydantic import BaseModel
from pydantic import Field as PydanticField


class JobCreate(BaseModel):
    repo_url: str = PydanticField(..., min_length=1, max_length=500)
    repo_branch: str = "main"
    issue_number: int | None = None
    issue_title: str | None = None
    issue_body: str | None = None
    input_text: str | None = None


class JobUpdate(BaseModel):
    current_phase: str | None = None
    error_message: str | None = None
    artifacts: dict[str, Any] | None = None
    gate_decisions: list[Any] | None = None
