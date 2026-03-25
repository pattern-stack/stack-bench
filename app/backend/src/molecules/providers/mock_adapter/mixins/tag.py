# mypy: disable-error-code="attr-defined"
"""Mock implementation of TagProtocol."""

from __future__ import annotations

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateTagInput,
    Tag,
    TagFilter,
    UpdateTagInput,
)


class MockTagMixin:
    """In-memory TagProtocol implementation."""

    async def create_tag(self, input: CreateTagInput) -> Tag:
        tag_id = self._next_id("tag")
        data = {
            "id": tag_id,
            "name": input.name,
            "color": input.color,
            "description": input.description,
            "group": input.group,
            "is_exclusive": input.is_exclusive,
        }
        self._tags[tag_id] = data
        return Tag(**data)

    async def get_tag(self, id: str) -> Tag:
        if id not in self._tags:
            raise NotFoundError("Tag", id)
        return Tag(**self._tags[id])

    async def update_tag(self, input: UpdateTagInput) -> Tag:
        if input.id not in self._tags:
            raise NotFoundError("Tag", input.id)
        data = self._tags[input.id]
        for field in ("name", "color", "description", "group", "is_exclusive"):
            value = getattr(input, field)
            if value is not None:
                data[field] = value
        return Tag(**data)

    async def list_tags(self, filter: TagFilter | None = None) -> list[Tag]:
        results = list(self._tags.values())
        if filter is not None:
            if filter.group is not None:
                group_val = filter.group.value if hasattr(filter.group, "value") else filter.group
                results = [
                    t
                    for t in results
                    if (t["group"].value if hasattr(t["group"], "value") else t["group"]) == group_val
                ]
            if filter.is_exclusive is not None:
                results = [t for t in results if t["is_exclusive"] == filter.is_exclusive]
        return [Tag(**t) for t in results]

    async def delete_tag(self, id: str) -> None:
        if id not in self._tags:
            raise NotFoundError("Tag", id)
        del self._tags[id]
        # Clean up entity_tags references
        for entity_id in self._entity_tags:
            self._entity_tags[entity_id].discard(id)

    async def create_tags(self, inputs: list[CreateTagInput]) -> list[Tag]:
        return [await self.create_tag(i) for i in inputs]

    async def get_tags(self, ids: list[str]) -> list[Tag]:
        return [await self.get_tag(id) for id in ids]

    async def delete_tags(self, ids: list[str]) -> None:
        for id in ids:
            await self.delete_tag(id)

    # -- entity-tag associations --

    async def apply_tag(self, entity_id: str, tag_id: str) -> None:
        if tag_id not in self._tags:
            raise NotFoundError("Tag", tag_id)
        if entity_id not in self._entity_tags:
            self._entity_tags[entity_id] = set()
        self._entity_tags[entity_id].add(tag_id)

    async def remove_tag(self, entity_id: str, tag_id: str) -> None:
        if entity_id in self._entity_tags:
            self._entity_tags[entity_id].discard(tag_id)

    async def get_entity_tags(self, entity_id: str) -> list[Tag]:
        tag_ids = self._entity_tags.get(entity_id, set())
        return [Tag(**self._tags[tid]) for tid in tag_ids if tid in self._tags]

    async def apply_tags(self, entity_id: str, tag_ids: list[str]) -> None:
        for tag_id in tag_ids:
            await self.apply_tag(entity_id, tag_id)

    async def remove_tags(self, entity_id: str, tag_ids: list[str]) -> None:
        for tag_id in tag_ids:
            await self.remove_tag(entity_id, tag_id)

    async def set_entity_tags(self, entity_id: str, tag_ids: list[str]) -> None:
        self._entity_tags[entity_id] = set(tag_ids)

    async def apply_tag_to_entities(self, tag_id: str, entity_ids: list[str]) -> None:
        if tag_id not in self._tags:
            raise NotFoundError("Tag", tag_id)
        for entity_id in entity_ids:
            if entity_id not in self._entity_tags:
                self._entity_tags[entity_id] = set()
            self._entity_tags[entity_id].add(tag_id)

    async def get_entities_tags(self, entity_ids: list[str]) -> dict[str, list[Tag]]:
        result: dict[str, list[Tag]] = {}
        for entity_id in entity_ids:
            result[entity_id] = await self.get_entity_tags(entity_id)
        return result
