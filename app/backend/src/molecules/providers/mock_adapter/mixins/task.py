# mypy: disable-error-code="attr-defined"
"""Mock implementation of TaskProtocol."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agentic_patterns.core.atoms.exceptions import ConflictError, NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateTaskInput,
    Relation,
    RelationDirection,
    RelationType,
    StatusCategory,
    Task,
    TaskFilter,
    UpdateTaskInput,
    WorkPhase,
)


class MockTaskMixin:
    """In-memory TaskProtocol implementation."""

    # -- single operations --

    async def create_task(self, input: CreateTaskInput) -> Task:
        now = datetime.now(UTC)
        task_id = self._next_id("task")
        data = {
            "id": task_id,
            "title": input.title,
            "description": input.description,
            "phase": input.phase,
            "status_category": input.status_category,
            "issue_type": input.issue_type,
            "priority": input.priority,
            "status": input.status_category,  # mirror status_category as status string
            "assignee_id": input.assignee_id,
            "project_id": input.project_id,
            "tag_ids": list(input.tag_ids),
            "created_at": now,
            "updated_at": now,
        }
        self._tasks[task_id] = data
        return Task(**data)

    async def get_task(self, id: str) -> Task:
        if id not in self._tasks:
            raise NotFoundError("Task", id)
        return Task(**self._tasks[id])

    async def update_task(self, input: UpdateTaskInput) -> Task:
        if input.id not in self._tasks:
            raise NotFoundError("Task", input.id)
        data = self._tasks[input.id]
        for field in (
            "title",
            "description",
            "phase",
            "status_category",
            "issue_type",
            "priority",
            "assignee_id",
            "project_id",
        ):
            value = getattr(input, field)
            if value is not None:
                data[field] = value
        if input.status_category is not None:
            data["status"] = input.status_category
        data["updated_at"] = datetime.now(UTC)
        return Task(**data)

    async def list_tasks(self, filter: TaskFilter | None = None) -> list[Task]:
        results = list(self._tasks.values())
        if filter is not None:
            if filter.phase is not None:
                results = [t for t in results if t["phase"] == filter.phase]
            if filter.status_category is not None:
                results = [t for t in results if t["status_category"] == filter.status_category]
            if filter.issue_type is not None:
                results = [t for t in results if t["issue_type"] == filter.issue_type]
            if filter.assignee_id is not None:
                results = [t for t in results if t["assignee_id"] == filter.assignee_id]
            if filter.project_id is not None:
                results = [t for t in results if t["project_id"] == filter.project_id]
            if filter.tag_ids is not None:
                tag_set = set(filter.tag_ids)
                results = [t for t in results if tag_set.intersection(t.get("tag_ids", []))]
            if filter.has_blockers is not None:
                blocked_ids = self._get_blocked_task_ids()
                if filter.has_blockers:
                    results = [t for t in results if t["id"] in blocked_ids]
                else:
                    results = [t for t in results if t["id"] not in blocked_ids]
        return [Task(**t) for t in results]

    async def delete_task(self, id: str) -> None:
        if id not in self._tasks:
            raise NotFoundError("Task", id)
        del self._tasks[id]

    # -- bulk operations --

    async def create_tasks(self, inputs: list[CreateTaskInput]) -> list[Task]:
        return [await self.create_task(i) for i in inputs]

    async def get_tasks(self, ids: list[str]) -> list[Task]:
        return [await self.get_task(id) for id in ids]

    async def update_tasks(self, inputs: list[UpdateTaskInput]) -> list[Task]:
        return [await self.update_task(i) for i in inputs]

    async def delete_tasks(self, ids: list[str]) -> None:
        for id in ids:
            await self.delete_task(id)

    # -- phase advancement --

    async def advance_phase(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise NotFoundError("Task", task_id)
        data = self._tasks[task_id]
        phase = data["phase"]
        status_cat = data["status_category"]
        # Normalize enum values to strings for comparison
        phase_val = phase.value if hasattr(phase, "value") else phase
        status_val = status_cat.value if hasattr(status_cat, "value") else status_cat
        if phase_val != WorkPhase.PLANNING.value or status_val != StatusCategory.DONE.value:
            raise ConflictError(
                f"Cannot advance phase: requires PLANNING/DONE (got {phase_val}/{status_val})",
                entity_id=task_id,
            )
        data["phase"] = WorkPhase.IMPLEMENTATION.value
        data["status_category"] = StatusCategory.TODO.value
        data["status"] = StatusCategory.TODO.value
        data["updated_at"] = datetime.now(UTC)
        return Task(**data)

    # -- relations --

    async def add_relation(self, source_id: str, target_id: str, relation_type: RelationType) -> None:
        rel = {"source_id": source_id, "target_id": target_id, "relation_type": relation_type}
        self._relations.append(rel)

    async def remove_relation(self, source_id: str, target_id: str, relation_type: RelationType) -> None:
        rt_val = relation_type.value if hasattr(relation_type, "value") else relation_type
        self._relations[:] = [
            r
            for r in self._relations
            if not (
                r["source_id"] == source_id
                and r["target_id"] == target_id
                and (r["relation_type"].value if hasattr(r["relation_type"], "value") else r["relation_type"]) == rt_val
            )
        ]

    async def get_relations(
        self,
        task_id: str,
        relation_type: RelationType | None = None,
        direction: RelationDirection = RelationDirection.BOTH,
    ) -> list[Relation]:
        results: list[dict[str, Any]] = []
        dir_val = direction.value if hasattr(direction, "value") else direction
        for r in self._relations:
            if relation_type is not None:
                rt_val = relation_type.value if hasattr(relation_type, "value") else relation_type
                r_rt_val = r["relation_type"].value if hasattr(r["relation_type"], "value") else r["relation_type"]
                if r_rt_val != rt_val:
                    continue
            is_outgoing = dir_val in (RelationDirection.OUTGOING.value, RelationDirection.BOTH.value)
            is_incoming = dir_val in (RelationDirection.INCOMING.value, RelationDirection.BOTH.value)
            if (is_outgoing and r["source_id"] == task_id) or (is_incoming and r["target_id"] == task_id):
                results.append(r)
        return [Relation(**r) for r in results]

    async def add_relations(self, relations: list[Relation]) -> None:
        for rel in relations:
            await self.add_relation(rel.source_id, rel.target_id, RelationType(rel.relation_type))

    async def remove_relations(self, relations: list[Relation]) -> None:
        for rel in relations:
            await self.remove_relation(rel.source_id, rel.target_id, RelationType(rel.relation_type))

    # -- helpers --

    def _get_blocked_task_ids(self) -> set[str]:
        """Return set of task IDs that are blocked by another task."""
        blocked: set[str] = set()
        for r in self._relations:
            rt_val = r["relation_type"].value if hasattr(r["relation_type"], "value") else r["relation_type"]
            if rt_val == RelationType.BLOCKS.value:
                blocked.add(r["target_id"])
        return blocked
