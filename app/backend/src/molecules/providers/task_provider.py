from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ExternalTask:
    """DTO for a task from an external provider."""

    external_id: str
    title: str
    description: str | None = None
    state: str | None = None
    priority: str | None = None
    assignee_id: str | None = None
    labels: list[str] | None = None
    url: str | None = None
    provider: str = "local"


@dataclass
class ExternalComment:
    """DTO for a comment from an external provider."""

    external_id: str
    body: str
    author_id: str | None = None
    url: str | None = None


@dataclass
class SyncResult:
    """Result of a sync operation."""

    created: int = 0
    updated: int = 0
    deleted: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: SyncResult) -> SyncResult:
        """Merge another SyncResult into this one."""
        return SyncResult(
            created=self.created + other.created,
            updated=self.updated + other.updated,
            deleted=self.deleted + other.deleted,
            errors=[*self.errors, *other.errors],
        )


class TaskProvider(Protocol):
    """Contract for external task management providers."""

    async def list_tasks(self, project_id: str | None = None) -> list[ExternalTask]: ...

    async def get_task(self, external_id: str) -> ExternalTask | None: ...

    async def create_task(self, task: ExternalTask) -> ExternalTask: ...

    async def update_task(self, external_id: str, task: ExternalTask) -> ExternalTask: ...

    async def list_comments(self, task_external_id: str) -> list[ExternalComment]: ...

    async def create_comment(self, task_external_id: str, comment: ExternalComment) -> ExternalComment: ...
