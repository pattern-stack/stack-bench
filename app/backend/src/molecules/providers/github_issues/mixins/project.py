"""GitHub Issues implementation of ProjectProtocol.

GitHub doesn't have a native project concept at the issue level that maps
cleanly to our protocol. GitHub Projects v2 uses a complex GraphQL API.

This implementation uses a simple approach: "meta-issues" with a special
label (meta:project) represent projects. This is a lightweight convention
that works within the Issues REST API.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateProjectInput,
    Project,
    ProjectFilter,
    ProjectStatus,
    UpdateProjectInput,
)

if TYPE_CHECKING:
    from ..client import GitHubClient

PROJECT_LABEL = "meta:project"


class GitHubProjectMixin:
    """GitHub meta-issues as ProjectProtocol implementation.

    Projects are represented as GitHub issues with the "meta:project" label.
    Project status is encoded in labels: "project-status:active", etc.
    """

    client: GitHubClient
    owner: str
    repo: str

    @property
    def _repo_path(self) -> str:
        return f"/repos/{self.owner}/{self.repo}"

    # -- helpers --

    _PROJECT_STATUS_LABELS: dict[str, ProjectStatus] = {
        "project-status:backlog": ProjectStatus.BACKLOG,
        "project-status:planning": ProjectStatus.PLANNING,
        "project-status:active": ProjectStatus.ACTIVE,
        "project-status:on-hold": ProjectStatus.ON_HOLD,
        "project-status:completed": ProjectStatus.COMPLETED,
        "project-status:archived": ProjectStatus.ARCHIVED,
    }
    _REVERSE_PROJECT_STATUS: dict[ProjectStatus, str] = {v: k for k, v in _PROJECT_STATUS_LABELS.items()}

    def _to_project(self, data: dict[str, Any]) -> Project:
        """Convert a GitHub issue (meta:project) JSON to a Project."""
        labels = [lbl["name"] for lbl in data.get("labels", [])]

        # Extract project status from labels
        status_category = ProjectStatus.BACKLOG
        status_str: str | None = None
        for label in labels:
            if label in self._PROJECT_STATUS_LABELS:
                status_category = self._PROJECT_STATUS_LABELS[label]
                status_str = label
                break

        # If closed and no explicit status label, mark as completed
        if data.get("state") == "closed" and status_str is None:
            status_category = ProjectStatus.COMPLETED

        # Assignee as lead
        lead_id: str | None = None
        assignee = data.get("assignee")
        if assignee:
            lead_id = str(assignee["id"])

        return Project(
            id=str(data["number"]),
            name=data["title"],
            description=data.get("body"),
            status_category=status_category,
            status=status_str,
            lead_id=lead_id,
            team_ids=[],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    # -- CRUD --

    async def create_project(self, input: CreateProjectInput) -> Project:
        labels = [PROJECT_LABEL]
        status_label = self._REVERSE_PROJECT_STATUS.get(input.status_category)
        if status_label:
            labels.append(status_label)

        body: dict[str, Any] = {
            "title": input.name,
            "labels": labels,
        }
        if input.description:
            body["body"] = input.description
        if input.lead_id:
            body["assignees"] = [input.lead_id]

        # Ensure the meta:project label exists
        try:
            await self.client.get(f"{self._repo_path}/labels/{PROJECT_LABEL}")
        except Exception:
            await self.client.post(
                f"{self._repo_path}/labels",
                json={
                    "name": PROJECT_LABEL,
                    "color": "0e8a16",
                    "description": "Meta-issue representing a project",
                },
            )

        data = await self.client.post(f"{self._repo_path}/issues", json=body)
        return self._to_project(data)

    async def get_project(self, id: str) -> Project:
        try:
            data = await self.client.get(f"{self._repo_path}/issues/{id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Project", id) from e
            raise

        # Verify it's actually a project
        labels = [lbl["name"] for lbl in data.get("labels", [])]
        if PROJECT_LABEL not in labels:
            raise NotFoundError("Project", id)

        return self._to_project(data)

    async def update_project(self, input: UpdateProjectInput) -> Project:
        # Verify it exists and is a project
        await self.get_project(input.id)

        current = await self.client.get(f"{self._repo_path}/issues/{input.id}")
        current_labels = [lbl["name"] for lbl in current.get("labels", [])]

        body: dict[str, Any] = {}
        if input.name is not None:
            body["title"] = input.name
        if input.description is not None:
            body["body"] = input.description

        # Rebuild labels: keep non-project-status labels, update status
        new_labels = [lbl for lbl in current_labels if not lbl.startswith("project-status:")]
        if input.status_category is not None:
            status_label = self._REVERSE_PROJECT_STATUS.get(input.status_category)
            if status_label:
                new_labels.append(status_label)

            # Close/open based on status
            if input.status_category in (
                ProjectStatus.COMPLETED,
                ProjectStatus.ARCHIVED,
            ):
                body["state"] = "closed"
            else:
                body["state"] = "open"
        body["labels"] = new_labels

        if input.lead_id is not None:
            body["assignees"] = [input.lead_id] if input.lead_id else []

        data = await self.client.patch(f"{self._repo_path}/issues/{input.id}", json=body)
        return self._to_project(data)

    async def list_projects(self, filter: ProjectFilter | None = None) -> list[Project]:
        params: dict[str, Any] = {"state": "all", "labels": PROJECT_LABEL}

        items = await self.client.get_paginated(f"{self._repo_path}/issues", params=params)
        projects = [self._to_project(item) for item in items]

        if filter is not None:
            if filter.status_category is not None:
                projects = [p for p in projects if p.status_category == filter.status_category]
            if filter.lead_id is not None:
                projects = [p for p in projects if p.lead_id == filter.lead_id]
            if filter.team_id is not None:
                projects = [p for p in projects if filter.team_id in p.team_ids]

        return projects

    async def delete_project(self, id: str) -> None:
        """Close the project meta-issue."""
        await self.get_project(id)  # Verify it exists
        await self.client.patch(
            f"{self._repo_path}/issues/{id}",
            json={"state": "closed", "labels": [PROJECT_LABEL, "meta:deleted"]},
        )

    async def get_projects(self, ids: list[str]) -> list[Project]:
        return [await self.get_project(id) for id in ids]

    async def update_projects(self, inputs: list[UpdateProjectInput]) -> list[Project]:
        return [await self.update_project(i) for i in inputs]
