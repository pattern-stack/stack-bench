"""GitHub Issues implementation of TagProtocol via labels."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateTagInput,
    Tag,
    TagFilter,
    UpdateTagInput,
)

from ..constants import label_to_tag_group

if TYPE_CHECKING:
    from ..client import GitHubClient


class GitHubTagMixin:
    """GitHub labels as TagProtocol implementation.

    Label names are used as tag IDs (they're unique within a repo).
    """

    client: GitHubClient
    owner: str
    repo: str

    @property
    def _repo_path(self) -> str:
        return f"/repos/{self.owner}/{self.repo}"

    # -- helpers --

    def _to_tag(self, data: dict[str, Any]) -> Tag:
        """Convert a GitHub label JSON to a Tag."""
        name = data["name"]
        color = data.get("color")
        if color and not color.startswith("#"):
            color = f"#{color}"

        return Tag(
            id=name,  # Use label name as ID (unique per repo)
            name=name,
            color=color,
            description=data.get("description"),
            group=label_to_tag_group(name),
            is_exclusive=name.startswith(("phase:", "status:", "priority:")),
        )

    # -- CRUD --

    async def create_tag(self, input: CreateTagInput) -> Tag:
        color = input.color
        if color and color.startswith("#"):
            color = color[1:]  # GitHub expects color without #

        body: dict[str, Any] = {"name": input.name}
        if color:
            body["color"] = color
        if input.description:
            body["description"] = input.description

        data = await self.client.post(f"{self._repo_path}/labels", json=body)
        return self._to_tag(data)

    async def get_tag(self, id: str) -> Tag:
        try:
            data = await self.client.get(f"{self._repo_path}/labels/{id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Tag", id) from e
            raise
        return self._to_tag(data)

    async def update_tag(self, input: UpdateTagInput) -> Tag:
        body: dict[str, Any] = {}
        if input.name is not None:
            body["new_name"] = input.name
        if input.color is not None:
            color = input.color
            if color.startswith("#"):
                color = color[1:]
            body["color"] = color
        if input.description is not None:
            body["description"] = input.description

        if not body:
            return await self.get_tag(input.id)

        try:
            data = await self.client.patch(f"{self._repo_path}/labels/{input.id}", json=body)
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Tag", input.id) from e
            raise
        return self._to_tag(data)

    async def list_tags(self, filter: TagFilter | None = None) -> list[Tag]:
        items = await self.client.get_paginated(f"{self._repo_path}/labels")
        tags = [self._to_tag(item) for item in items]

        if filter is not None:
            if filter.group is not None:
                tags = [t for t in tags if t.group == filter.group]
            if filter.is_exclusive is not None:
                tags = [t for t in tags if t.is_exclusive == filter.is_exclusive]

        return tags

    async def delete_tag(self, id: str) -> None:
        try:
            await self.client.delete(f"{self._repo_path}/labels/{id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Tag", id) from e
            raise

    # -- bulk CRUD --

    async def create_tags(self, inputs: list[CreateTagInput]) -> list[Tag]:
        return [await self.create_tag(i) for i in inputs]

    async def get_tags(self, ids: list[str]) -> list[Tag]:
        return [await self.get_tag(id) for id in ids]

    async def delete_tags(self, ids: list[str]) -> None:
        for id in ids:
            await self.delete_tag(id)

    # -- entity-tag associations (issue-label) --

    async def apply_tag(self, entity_id: str, tag_id: str) -> None:
        """Add a label to an issue."""
        await self.client.post(
            f"{self._repo_path}/issues/{entity_id}/labels",
            json={"labels": [tag_id]},
        )

    async def remove_tag(self, entity_id: str, tag_id: str) -> None:
        """Remove a label from an issue."""
        with contextlib.suppress(Exception):
            await self.client.delete(f"{self._repo_path}/issues/{entity_id}/labels/{tag_id}")

    async def get_entity_tags(self, entity_id: str) -> list[Tag]:
        """Get all labels on an issue."""
        items = await self.client.get_paginated(f"{self._repo_path}/issues/{entity_id}/labels")
        return [self._to_tag(item) for item in items]

    async def apply_tags(self, entity_id: str, tag_ids: list[str]) -> None:
        if tag_ids:
            await self.client.post(
                f"{self._repo_path}/issues/{entity_id}/labels",
                json={"labels": tag_ids},
            )

    async def remove_tags(self, entity_id: str, tag_ids: list[str]) -> None:
        for tag_id in tag_ids:
            await self.remove_tag(entity_id, tag_id)

    async def set_entity_tags(self, entity_id: str, tag_ids: list[str]) -> None:
        """Replace all labels on an issue."""
        await self.client.patch(
            f"{self._repo_path}/issues/{entity_id}",
            json={"labels": tag_ids},
        )

    async def apply_tag_to_entities(self, tag_id: str, entity_ids: list[str]) -> None:
        for entity_id in entity_ids:
            await self.apply_tag(entity_id, tag_id)

    async def get_entities_tags(self, entity_ids: list[str]) -> dict[str, list[Tag]]:
        result: dict[str, list[Tag]] = {}
        for entity_id in entity_ids:
            result[entity_id] = await self.get_entity_tags(entity_id)
        return result
