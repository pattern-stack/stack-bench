from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GitHubConnectionResponse(BaseModel):
    id: UUID
    github_user_id: int
    github_login: str
    token_expires_at: datetime | None = None
    connected: bool = True  # computed: always True if record exists
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
