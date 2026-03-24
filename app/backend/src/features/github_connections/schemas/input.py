from datetime import datetime

from pydantic import BaseModel


class GitHubConnectionCreate(BaseModel):
    github_user_id: int
    github_login: str
    tokens_encrypted: bytes
    token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None


class GitHubConnectionUpdate(BaseModel):
    tokens_encrypted: bytes | None = None
    github_login: str | None = None
    token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None
