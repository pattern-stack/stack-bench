# mypy: disable-error-code="attr-defined,has-type"
"""Mock implementation of CommentProtocol."""

from __future__ import annotations

from datetime import UTC, datetime

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import Comment, Reaction


class MockCommentMixin:
    """In-memory CommentProtocol implementation."""

    async def create_comment(self, issue_id: str, body: str, parent_id: str | None = None) -> Comment:
        now = datetime.now(UTC)
        comment_id = self._next_id("comment")
        data = {
            "id": comment_id,
            "body": body,
            "issue_id": issue_id,
            "author_id": self._current_user_id,
            "parent_id": parent_id,
            "created_at": now,
            "updated_at": now,
            "edited_at": None,
        }
        self._comments[comment_id] = data
        return Comment(**data)

    async def get_comment(self, id: str) -> Comment:
        if id not in self._comments:
            raise NotFoundError("Comment", id)
        return Comment(**self._comments[id])

    async def list_comments(self, issue_id: str) -> list[Comment]:
        return [Comment(**c) for c in self._comments.values() if c["issue_id"] == issue_id]

    async def update_comment(self, id: str, body: str) -> Comment:
        if id not in self._comments:
            raise NotFoundError("Comment", id)
        now = datetime.now(UTC)
        data = self._comments[id]
        data["body"] = body
        data["updated_at"] = now
        data["edited_at"] = now
        return Comment(**data)

    async def delete_comment(self, id: str) -> None:
        if id not in self._comments:
            raise NotFoundError("Comment", id)
        del self._comments[id]
        # Also clean up reactions for this comment
        self._reactions = {k: v for k, v in self._reactions.items() if v["comment_id"] != id}

    async def add_reaction(self, comment_id: str, emoji: str) -> Reaction:
        if comment_id not in self._comments:
            raise NotFoundError("Comment", comment_id)
        reaction_id = self._next_id("reaction")
        data = {
            "id": reaction_id,
            "emoji": emoji,
            "user_id": self._current_user_id,
            "comment_id": comment_id,
        }
        self._reactions[reaction_id] = data
        return Reaction(**data)

    async def remove_reaction(self, comment_id: str, emoji: str) -> None:
        if comment_id not in self._comments:
            raise NotFoundError("Comment", comment_id)
        user_id = self._current_user_id
        to_remove = [
            k
            for k, v in self._reactions.items()
            if v["comment_id"] == comment_id and v["emoji"] == emoji and v["user_id"] == user_id
        ]
        for k in to_remove:
            del self._reactions[k]

    async def list_reactions(self, comment_id: str) -> list[Reaction]:
        if comment_id not in self._comments:
            raise NotFoundError("Comment", comment_id)
        return [Reaction(**v) for v in self._reactions.values() if v["comment_id"] == comment_id]
