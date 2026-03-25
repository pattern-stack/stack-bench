# mypy: disable-error-code="attr-defined"
"""Mock implementation of SprintProtocol."""

from __future__ import annotations

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateSprintInput,
    Sprint,
    SprintStatus,
    Task,
    UpdateSprintInput,
)


class MockSprintMixin:
    """In-memory SprintProtocol implementation."""

    async def get_sprint(self, id: str) -> Sprint:
        if id not in self._sprints:
            raise NotFoundError("Sprint", id)
        return Sprint(**self._sprints[id])

    async def get_active_sprint(self) -> Sprint | None:
        for s in self._sprints.values():
            status_val = s["status"].value if hasattr(s["status"], "value") else s["status"]
            if status_val == SprintStatus.ACTIVE.value:
                return Sprint(**s)
        return None

    async def list_sprints(self, status: SprintStatus | None = None) -> list[Sprint]:
        results = list(self._sprints.values())
        if status is not None:
            status_val = status.value if hasattr(status, "value") else status
            results = [
                s
                for s in results
                if (s["status"].value if hasattr(s["status"], "value") else s["status"]) == status_val
            ]
        return [Sprint(**s) for s in results]

    async def get_sprint_issues(self, sprint_id: str) -> list[Task]:
        if sprint_id not in self._sprints:
            raise NotFoundError("Sprint", sprint_id)
        issue_ids = self._sprint_issues.get(sprint_id, set())
        tasks = []
        for iid in issue_ids:
            if iid in self._tasks:
                tasks.append(Task(**self._tasks[iid]))
        return tasks

    async def create_sprint(self, input: CreateSprintInput) -> Sprint:
        sprint_id = self._next_id("sprint")
        # Auto-number sprints
        number = len(self._sprints) + 1
        name = input.name or f"Sprint {number}"
        data = {
            "id": sprint_id,
            "name": name,
            "number": number,
            "starts_at": input.starts_at,
            "ends_at": input.ends_at,
            "status": SprintStatus.PLANNED.value,
            "team_id": "mock-team-1",
            "description": input.description,
            "completed_at": None,
        }
        self._sprints[sprint_id] = data
        self._sprint_issues[sprint_id] = set()
        return Sprint(**data)

    async def update_sprint(self, input: UpdateSprintInput) -> Sprint:
        if input.id not in self._sprints:
            raise NotFoundError("Sprint", input.id)
        data = self._sprints[input.id]
        for field in ("name", "starts_at", "ends_at", "description"):
            value = getattr(input, field)
            if value is not None:
                data[field] = value
        return Sprint(**data)

    async def add_to_sprint(self, issue_id: str, sprint_id: str) -> None:
        if sprint_id not in self._sprints:
            raise NotFoundError("Sprint", sprint_id)
        if sprint_id not in self._sprint_issues:
            self._sprint_issues[sprint_id] = set()
        self._sprint_issues[sprint_id].add(issue_id)

    async def remove_from_sprint(self, issue_id: str) -> None:
        for _sprint_id, issues in self._sprint_issues.items():
            issues.discard(issue_id)
