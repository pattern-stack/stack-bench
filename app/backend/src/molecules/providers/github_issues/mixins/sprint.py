"""GitHub Issues implementation of SprintProtocol via milestones."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateSprintInput,
    Sprint,
    SprintStatus,
    Task,
    UpdateSprintInput,
)

if TYPE_CHECKING:
    from ..client import GitHubClient


class GitHubSprintMixin:
    """GitHub milestones as SprintProtocol implementation."""

    client: GitHubClient
    owner: str
    repo: str

    @property
    def _repo_path(self) -> str:
        return f"/repos/{self.owner}/{self.repo}"

    # -- helpers --

    def _to_sprint(self, data: dict[str, Any]) -> Sprint:
        """Convert a GitHub milestone JSON to a Sprint."""
        state = data.get("state", "open")

        # Determine sprint status from milestone state and dates
        if state == "closed":
            status = SprintStatus.COMPLETED
        else:
            due_on = data.get("due_on")
            status = SprintStatus.ACTIVE if due_on else SprintStatus.PLANNED

        # GitHub milestones don't have explicit start dates
        created_at_str = data.get("created_at", datetime.now(UTC).isoformat())
        due_on_str = data.get("due_on")

        starts_at = datetime.fromisoformat(created_at_str)
        ends_at = (
            datetime.fromisoformat(due_on_str)
            if due_on_str
            else starts_at  # No due date — use created_at as placeholder
        )

        closed_at = data.get("closed_at")
        completed_at = datetime.fromisoformat(closed_at) if closed_at else None

        return Sprint(
            id=str(data["number"]),
            name=data["title"],
            number=data["number"],
            starts_at=starts_at,
            ends_at=ends_at,
            status=status,
            team_id=f"{self.owner}/{self.repo}",
            description=data.get("description"),
            completed_at=completed_at,
        )

    # -- queries --

    async def get_sprint(self, id: str) -> Sprint:
        try:
            data = await self.client.get(f"{self._repo_path}/milestones/{id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Sprint", id) from e
            raise
        return self._to_sprint(data)

    async def get_active_sprint(self) -> Sprint | None:
        """Return the most recently created open milestone."""
        items = await self.client.get_paginated(
            f"{self._repo_path}/milestones",
            params={"state": "open", "sort": "due_on", "direction": "desc"},
        )
        if not items:
            return None
        return self._to_sprint(items[0])

    async def list_sprints(self, status: SprintStatus | None = None) -> list[Sprint]:
        # Map SprintStatus to GitHub milestone state
        if status == SprintStatus.COMPLETED:
            gh_state = "closed"
        elif status is not None:
            gh_state = "open"
        else:
            gh_state = "all"

        items = await self.client.get_paginated(
            f"{self._repo_path}/milestones",
            params={"state": gh_state, "sort": "due_on", "direction": "desc"},
        )
        sprints = [self._to_sprint(item) for item in items]

        # Client-side filter for PLANNED vs ACTIVE (both are "open" in GH)
        if status is not None and status in (SprintStatus.PLANNED, SprintStatus.ACTIVE):
            sprints = [s for s in sprints if s.status == status]

        return sprints

    async def get_sprint_issues(self, sprint_id: str) -> list[Task]:
        """Get all issues in a milestone."""
        # Verify milestone exists
        try:
            await self.client.get(f"{self._repo_path}/milestones/{sprint_id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Sprint", sprint_id) from e
            raise

        items = await self.client.get_paginated(
            f"{self._repo_path}/issues",
            params={"milestone": sprint_id, "state": "all"},
        )
        # Filter out PRs and convert
        # Import here to avoid circular — _to_task is from TaskMixin
        tasks = []
        for item in items:
            if "pull_request" not in item:
                tasks.append(self._to_task(item))  # type: ignore[attr-defined]
        return tasks

    # -- mutations --

    async def create_sprint(self, input: CreateSprintInput) -> Sprint:
        body: dict[str, Any] = {
            "due_on": input.ends_at.isoformat(),
        }
        if input.name:
            body["title"] = input.name
        else:
            # Auto-generate name
            existing = await self.client.get_paginated(f"{self._repo_path}/milestones", params={"state": "all"})
            body["title"] = f"Sprint {len(existing) + 1}"

        if input.description:
            body["description"] = input.description

        data = await self.client.post(f"{self._repo_path}/milestones", json=body)
        return self._to_sprint(data)

    async def update_sprint(self, input: UpdateSprintInput) -> Sprint:
        body: dict[str, Any] = {}
        if input.name is not None:
            body["title"] = input.name
        if input.ends_at is not None:
            body["due_on"] = input.ends_at.isoformat()
        if input.description is not None:
            body["description"] = input.description

        if not body:
            return await self.get_sprint(input.id)

        try:
            data = await self.client.patch(f"{self._repo_path}/milestones/{input.id}", json=body)
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Sprint", input.id) from e
            raise
        return self._to_sprint(data)

    async def add_to_sprint(self, issue_id: str, sprint_id: str) -> None:
        """Add an issue to a milestone (sprint)."""
        await self.client.patch(
            f"{self._repo_path}/issues/{issue_id}",
            json={"milestone": int(sprint_id)},
        )

    async def remove_from_sprint(self, issue_id: str) -> None:
        """Remove an issue from its milestone."""
        await self.client.patch(
            f"{self._repo_path}/issues/{issue_id}",
            json={"milestone": None},
        )
