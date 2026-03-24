# mypy: disable-error-code="attr-defined"
"""Mock implementation of ProjectProtocol."""

from __future__ import annotations

from datetime import UTC, datetime

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateProjectInput,
    Project,
    ProjectFilter,
    UpdateProjectInput,
)


class MockProjectMixin:
    """In-memory ProjectProtocol implementation."""

    async def create_project(self, input: CreateProjectInput) -> Project:
        now = datetime.now(UTC)
        project_id = self._next_id("project")
        data = {
            "id": project_id,
            "name": input.name,
            "description": input.description,
            "status_category": input.status_category,
            "status": None,
            "lead_id": input.lead_id,
            "team_ids": list(input.team_ids),
            "created_at": now,
            "updated_at": now,
        }
        self._projects[project_id] = data
        return Project(**data)

    async def get_project(self, id: str) -> Project:
        if id not in self._projects:
            raise NotFoundError("Project", id)
        return Project(**self._projects[id])

    async def update_project(self, input: UpdateProjectInput) -> Project:
        if input.id not in self._projects:
            raise NotFoundError("Project", input.id)
        data = self._projects[input.id]
        for field in ("name", "description", "status_category", "lead_id"):
            value = getattr(input, field)
            if value is not None:
                data[field] = value
        data["updated_at"] = datetime.now(UTC)
        return Project(**data)

    async def list_projects(self, filter: ProjectFilter | None = None) -> list[Project]:
        results = list(self._projects.values())
        if filter is not None:
            if filter.status_category is not None:
                results = [p for p in results if p["status_category"] == filter.status_category]
            if filter.lead_id is not None:
                results = [p for p in results if p["lead_id"] == filter.lead_id]
            if filter.team_id is not None:
                results = [p for p in results if filter.team_id in p.get("team_ids", [])]
        return [Project(**p) for p in results]

    async def delete_project(self, id: str) -> None:
        if id not in self._projects:
            raise NotFoundError("Project", id)
        del self._projects[id]

    async def get_projects(self, ids: list[str]) -> list[Project]:
        return [await self.get_project(id) for id in ids]

    async def update_projects(self, inputs: list[UpdateProjectInput]) -> list[Project]:
        return [await self.update_project(i) for i in inputs]
