from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import GitHubConnection
from .schemas.input import GitHubConnectionCreate, GitHubConnectionUpdate


class GitHubConnectionService(BaseService[GitHubConnection, GitHubConnectionCreate, GitHubConnectionUpdate]):
    model = GitHubConnection

    async def get_by_github_user_id(self, db: AsyncSession, github_user_id: int) -> GitHubConnection | None:
        """Look up connection by GitHub user ID."""
        result = await db.execute(
            select(GitHubConnection).where(GitHubConnection.github_user_id == github_user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, db: AsyncSession, data: GitHubConnectionCreate) -> GitHubConnection:
        """Create or update connection (re-authorization replaces tokens)."""
        existing = await self.get_by_github_user_id(db, data.github_user_id)
        if existing:
            update_data = GitHubConnectionUpdate(
                tokens_encrypted=data.tokens_encrypted,
                github_login=data.github_login,
                token_expires_at=data.token_expires_at,
                refresh_token_expires_at=data.refresh_token_expires_at,
            )
            updated = await self.update(db, existing.id, update_data)
            if updated is None:
                raise RuntimeError(f"Failed to update GitHubConnection {existing.id}")
            return updated
        return await self.create(db, data)
