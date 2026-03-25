"""MockAdapter — in-memory implementation of all 7 protocol mixins."""

from __future__ import annotations

from typing import Any

from .mixins import (
    MockCommentMixin,
    MockDocumentMixin,
    MockProjectMixin,
    MockSprintMixin,
    MockTagMixin,
    MockTaskMixin,
    MockUserMixin,
)


class MockAdapter(
    MockTaskMixin,
    MockCommentMixin,
    MockProjectMixin,
    MockSprintMixin,
    MockTagMixin,
    MockUserMixin,
    MockDocumentMixin,
):
    """Composite mock adapter implementing all task management protocols.

    All data is stored in-memory dicts. Call ``reset()`` to clear all state.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Clear all in-memory storage and re-seed defaults."""
        # ID counter
        self._id_counter: int = 0

        # Tasks
        self._tasks: dict[str, dict[str, Any]] = {}
        self._relations: list[dict[str, Any]] = []

        # Comments
        self._comments: dict[str, dict[str, Any]] = {}
        self._reactions: dict[str, dict[str, Any]] = {}

        # Projects
        self._projects: dict[str, dict[str, Any]] = {}

        # Sprints
        self._sprints: dict[str, dict[str, Any]] = {}
        self._sprint_issues: dict[str, set[str]] = {}

        # Tags
        self._tags: dict[str, dict[str, Any]] = {}
        self._entity_tags: dict[str, set[str]] = {}

        # Users (pre-seeded)
        self._users: dict[str, dict[str, Any]] = {
            "mock-user-1": {
                "id": "mock-user-1",
                "name": "Mock User",
                "email": "mock@example.com",
                "user_type": "human",
                "role": "admin",
                "is_active": True,
                "avatar_url": None,
            },
        }
        self._teams: dict[str, dict[str, Any]] = {
            "mock-team-1": {
                "id": "mock-team-1",
                "name": "Mock Team",
                "key": "MOCK",
                "description": "Default mock team",
                "member_ids": ["mock-user-1"],
            },
        }
        self._current_user_id: str = "mock-user-1"

        # Documents
        self._documents: dict[str, dict[str, Any]] = {}

    def _next_id(self, prefix: str = "mock") -> str:
        """Generate a sequential mock ID."""
        self._id_counter += 1
        return f"{prefix}-{self._id_counter}"
