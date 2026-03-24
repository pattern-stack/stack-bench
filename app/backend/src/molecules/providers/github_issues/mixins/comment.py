"""GitHub Issues implementation of CommentProtocol."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import Comment, Reaction

if TYPE_CHECKING:
    from ..client import GitHubClient


class GitHubCommentMixin:
    """GitHub issue comments implementation of CommentProtocol."""

    client: GitHubClient
    owner: str
    repo: str

    @property
    def _repo_path(self) -> str:
        return f"/repos/{self.owner}/{self.repo}"

    # -- helpers --

    def _to_comment(self, data: dict[str, Any], issue_id: str | None = None) -> Comment:
        """Convert a GitHub issue comment JSON to a Comment."""
        # Extract issue_id from the issue_url if not provided
        if issue_id is None:
            issue_url = data.get("issue_url", "")
            # issue_url looks like: https://api.github.com/repos/owner/repo/issues/123
            parts = issue_url.rstrip("/").split("/")
            issue_id = parts[-1] if parts else "unknown"

        return Comment(
            id=str(data["id"]),
            body=data.get("body", ""),
            issue_id=issue_id,
            author_id=str(data["user"]["id"]) if data.get("user") else "unknown",
            parent_id=None,  # GitHub doesn't support threaded comments natively
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            edited_at=None,
        )

    def _to_reaction(self, data: dict[str, Any], comment_id: str) -> Reaction:
        """Convert a GitHub reaction JSON to a Reaction."""
        return Reaction(
            id=str(data["id"]),
            emoji=data["content"],
            user_id=str(data["user"]["id"]) if data.get("user") else "unknown",
            comment_id=comment_id,
        )

    # -- Comment CRUD --

    async def create_comment(
        self,
        issue_id: str,
        body: str,
        parent_id: str | None = None,
    ) -> Comment:
        """Create a comment on a GitHub issue.

        Note: parent_id is ignored — GitHub doesn't support threaded issue comments.
        """
        data = await self.client.post(
            f"{self._repo_path}/issues/{issue_id}/comments",
            json={"body": body},
        )
        return self._to_comment(data, issue_id=issue_id)

    async def get_comment(self, id: str) -> Comment:
        try:
            data = await self.client.get(f"{self._repo_path}/issues/comments/{id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Comment", id) from e
            raise
        return self._to_comment(data)

    async def list_comments(self, issue_id: str) -> list[Comment]:
        items = await self.client.get_paginated(f"{self._repo_path}/issues/{issue_id}/comments")
        return [self._to_comment(item, issue_id=issue_id) for item in items]

    async def update_comment(self, id: str, body: str) -> Comment:
        try:
            data = await self.client.patch(
                f"{self._repo_path}/issues/comments/{id}",
                json={"body": body},
            )
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Comment", id) from e
            raise
        return self._to_comment(data)

    async def delete_comment(self, id: str) -> None:
        try:
            await self.client.delete(f"{self._repo_path}/issues/comments/{id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Comment", id) from e
            raise

    # -- Reactions --

    async def add_reaction(self, comment_id: str, emoji: str) -> Reaction:
        data = await self.client.post(
            f"{self._repo_path}/issues/comments/{comment_id}/reactions",
            json={"content": emoji},
        )
        return self._to_reaction(data, comment_id=comment_id)

    async def remove_reaction(self, comment_id: str, emoji: str) -> None:
        """Remove a reaction by emoji. Finds the current user's reaction and deletes it."""
        reactions = await self.client.get_paginated(f"{self._repo_path}/issues/comments/{comment_id}/reactions")
        # Get current user to match reaction
        current_user = await self.client.get("/user")
        current_user_id = current_user["id"]

        for rxn in reactions:
            if rxn["content"] == emoji and rxn.get("user", {}).get("id") == current_user_id:
                await self.client.delete(f"{self._repo_path}/issues/comments/{comment_id}/reactions/{rxn['id']}")
                return

    async def list_reactions(self, comment_id: str) -> list[Reaction]:
        items = await self.client.get_paginated(f"{self._repo_path}/issues/comments/{comment_id}/reactions")
        return [self._to_reaction(item, comment_id=comment_id) for item in items]
