"""GitHub Issues implementation of TaskProtocol."""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import TYPE_CHECKING, Any

from agentic_patterns.core.atoms.exceptions import ConflictError, NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateTaskInput,
    IssueType,
    Priority,
    Relation,
    RelationDirection,
    RelationType,
    StatusCategory,
    Task,
    TaskFilter,
    UpdateTaskInput,
    WorkPhase,
)

from ..constants import (
    PHASE_LABELS,
    PRIORITY_LABELS,
    REVERSE_PHASE_LABELS,
    REVERSE_PRIORITY_LABELS,
    REVERSE_STATUS_LABELS,
    REVERSE_TYPE_LABELS,
    STATUS_LABELS,
    TYPE_LABELS,
)

if TYPE_CHECKING:
    from ..client import GitHubClient


class GitHubTaskMixin:
    """GitHub Issues TaskProtocol implementation.

    Maps GitHub issues to the Task protocol. Uses labels for
    phase, status, type, and priority encoding.
    """

    client: GitHubClient
    owner: str
    repo: str

    @property
    def _repo_path(self) -> str:
        return f"/repos/{self.owner}/{self.repo}"

    # -- helpers --

    def _to_task(self, data: dict[str, Any]) -> Task:
        """Convert a GitHub issue JSON object to a Task."""
        labels = [lbl["name"] for lbl in data.get("labels", [])]

        # Extract phase from labels
        phase = WorkPhase.PLANNING
        for label in labels:
            if label in PHASE_LABELS:
                phase = PHASE_LABELS[label]
                break

        # Extract status_category from labels, fall back to open/closed state
        status_category = StatusCategory.TODO
        for label in labels:
            if label in STATUS_LABELS:
                status_category = STATUS_LABELS[label]
                break
        else:
            # If no status label, infer from issue state
            if data.get("state") == "closed":
                # Check if cancelled
                if any(lbl in labels for lbl in ("status:cancelled",)):
                    status_category = StatusCategory.CANCELLED
                else:
                    status_category = StatusCategory.DONE

        # Extract issue type from labels
        issue_type: IssueType | None = None
        for label in labels:
            if label in TYPE_LABELS:
                issue_type = TYPE_LABELS[label]
                break

        # Extract priority from labels
        priority = Priority.NONE
        for label in labels:
            if label in PRIORITY_LABELS:
                priority = PRIORITY_LABELS[label]
                break

        # Assignee
        assignee_id: str | None = None
        assignee = data.get("assignee")
        if assignee:
            assignee_id = str(assignee["id"])

        # Milestone as project_id
        project_id: str | None = None
        milestone = data.get("milestone")
        if milestone:
            project_id = str(milestone["number"])

        # Tag IDs = label names (excluding our structured labels)
        tag_ids = [
            lbl
            for lbl in labels
            if not any(lbl.startswith(p) for p in ("phase:", "status:", "type:", "priority:", "meta:"))
        ]

        return Task(
            id=str(data["number"]),
            title=data["title"],
            description=data.get("body"),
            phase=phase,
            status_category=status_category,
            issue_type=issue_type,
            priority=priority,
            status=data["state"],
            assignee_id=assignee_id,
            project_id=project_id,
            tag_ids=tag_ids,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def _build_labels_for_task(
        self,
        phase: WorkPhase | None = None,
        status_category: StatusCategory | None = None,
        issue_type: IssueType | None = None,
        priority: Priority | None = None,
        extra_tag_ids: list[str] | None = None,
    ) -> list[str]:
        """Build the label list for a task create/update."""
        labels: list[str] = []
        if phase is not None:
            label = REVERSE_PHASE_LABELS.get(phase)
            if label:
                labels.append(label)
        if status_category is not None:
            label = REVERSE_STATUS_LABELS.get(status_category)
            if label:
                labels.append(label)
        if issue_type is not None:
            label = REVERSE_TYPE_LABELS.get(issue_type)
            if label:
                labels.append(label)
        if priority is not None and priority != Priority.NONE:
            label = REVERSE_PRIORITY_LABELS.get(priority)
            if label:
                labels.append(label)
        if extra_tag_ids:
            labels.extend(extra_tag_ids)
        return labels

    # -- CRUD --

    async def create_task(self, input: CreateTaskInput) -> Task:
        labels = self._build_labels_for_task(
            phase=input.phase,
            status_category=input.status_category,
            issue_type=input.issue_type,
            priority=input.priority,
            extra_tag_ids=input.tag_ids if input.tag_ids else None,
        )
        body: dict[str, Any] = {
            "title": input.title,
            "labels": labels,
        }
        if input.description:
            body["body"] = input.description
        if input.assignee_id:
            # GitHub expects a username for assignees, but we store user IDs.
            # Try using it directly — the caller should pass a username.
            body["assignees"] = [input.assignee_id]
        if input.project_id:
            # project_id maps to milestone number
            body["milestone"] = int(input.project_id)

        data = await self.client.post(f"{self._repo_path}/issues", json=body)
        return self._to_task(data)

    async def get_task(self, id: str) -> Task:
        try:
            data = await self.client.get(f"{self._repo_path}/issues/{id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Task", id) from e
            raise
        # GitHub returns pull requests via the issues endpoint too
        if "pull_request" in data:
            raise NotFoundError("Task", id)
        return self._to_task(data)

    async def update_task(self, input: UpdateTaskInput) -> Task:
        # First get the current issue to merge labels
        try:
            current = await self.client.get(f"{self._repo_path}/issues/{input.id}")
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Task", input.id) from e
            raise

        current_labels = [lbl["name"] for lbl in current.get("labels", [])]

        body: dict[str, Any] = {}
        if input.title is not None:
            body["title"] = input.title
        if input.description is not None:
            body["body"] = input.description

        # Rebuild labels: keep non-structured labels, replace structured ones
        new_labels = [
            lbl
            for lbl in current_labels
            if not any(lbl.startswith(p) for p in ("phase:", "status:", "type:", "priority:"))
        ]

        # Use new values or preserve current
        current_task = self._to_task(current)

        phase = input.phase if input.phase is not None else current_task.phase
        status_cat = input.status_category if input.status_category is not None else current_task.status_category
        issue_type = input.issue_type if input.issue_type is not None else current_task.issue_type
        priority = input.priority if input.priority is not None else current_task.priority

        structured_labels = self._build_labels_for_task(
            phase=phase,
            status_category=status_cat,
            issue_type=issue_type,
            priority=priority,
        )
        new_labels.extend(structured_labels)
        body["labels"] = new_labels

        # Handle state changes
        if input.status_category is not None:
            if input.status_category in (
                StatusCategory.DONE,
                StatusCategory.CANCELLED,
            ):
                body["state"] = "closed"
            else:
                body["state"] = "open"

        if input.assignee_id is not None:
            body["assignees"] = [input.assignee_id] if input.assignee_id else []

        if input.project_id is not None:
            body["milestone"] = int(input.project_id) if input.project_id else None

        data = await self.client.patch(f"{self._repo_path}/issues/{input.id}", json=body)
        return self._to_task(data)

    async def list_tasks(self, filter: TaskFilter | None = None) -> list[Task]:
        params: dict[str, Any] = {"state": "all", "per_page": 100}
        label_filters: list[str] = []

        if filter is not None:
            if filter.phase is not None:
                label = REVERSE_PHASE_LABELS.get(filter.phase)
                if label:
                    label_filters.append(label)
            if filter.status_category is not None:
                label = REVERSE_STATUS_LABELS.get(filter.status_category)
                if label:
                    label_filters.append(label)
                # Also filter by state
                if filter.status_category in (
                    StatusCategory.DONE,
                    StatusCategory.CANCELLED,
                ):
                    params["state"] = "closed"
                elif filter.status_category != StatusCategory.TODO:
                    params["state"] = "open"
            if filter.issue_type is not None:
                label = REVERSE_TYPE_LABELS.get(filter.issue_type)
                if label:
                    label_filters.append(label)
            if filter.assignee_id is not None:
                params["assignee"] = filter.assignee_id
            if filter.project_id is not None:
                params["milestone"] = filter.project_id

        if label_filters:
            params["labels"] = ",".join(label_filters)

        items = await self.client.get_paginated(f"{self._repo_path}/issues", params=params)

        # Filter out pull requests (GitHub includes them in issues endpoint)
        tasks = [self._to_task(item) for item in items if "pull_request" not in item]

        # Apply client-side filters that the API doesn't support
        if filter is not None:
            if filter.tag_ids is not None:
                tag_set = set(filter.tag_ids)
                tasks = [t for t in tasks if tag_set.intersection(t.tag_ids)]
            if filter.has_blockers is not None:
                # Relations aren't natively supported, skip this filter
                pass

        return tasks

    async def delete_task(self, id: str) -> None:
        """Close the issue and add a 'deleted' label (GitHub cannot truly delete issues)."""
        try:
            await self.client.patch(
                f"{self._repo_path}/issues/{id}",
                json={"state": "closed", "labels": ["meta:deleted"]},
            )
        except Exception as e:
            if "Not found" in str(e):
                raise NotFoundError("Task", id) from e
            raise

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
        """Advance a task from PLANNING/DONE to IMPLEMENTATION/TODO."""
        task = await self.get_task(task_id)
        if task.phase != WorkPhase.PLANNING or task.status_category != StatusCategory.DONE:
            raise ConflictError(
                f"Cannot advance phase: task must be in PLANNING phase with DONE status "
                f"(got phase={task.phase.value}, status={task.status_category.value})",
                entity_id=task_id,
            )

        return await self.update_task(
            UpdateTaskInput(
                id=task_id,
                phase=WorkPhase.IMPLEMENTATION,
                status_category=StatusCategory.TODO,
            )
        )

    # -- relations --
    # GitHub Issues doesn't have native relation support.
    # We use issue body cross-references as a simplified approach.
    # For now, relations are stored as labels: "blocks:#123", "parent-of:#456"

    async def add_relation(self, source_id: str, target_id: str, relation_type: RelationType) -> None:
        """Add a relation by adding a label to the source issue."""
        label = f"rel:{relation_type.value}:#{target_id}"
        await self.client.post(
            f"{self._repo_path}/issues/{source_id}/labels",
            json={"labels": [label]},
        )

    async def remove_relation(self, source_id: str, target_id: str, relation_type: RelationType) -> None:
        """Remove a relation by removing the label from the source issue."""
        label = f"rel:{relation_type.value}:#{target_id}"
        with contextlib.suppress(Exception):
            await self.client.delete(f"{self._repo_path}/issues/{source_id}/labels/{label}")

    async def get_relations(
        self,
        task_id: str,
        relation_type: RelationType | None = None,
        direction: RelationDirection = RelationDirection.BOTH,
    ) -> list[Relation]:
        """Get relations for a task by scanning relation labels."""
        relations: list[Relation] = []

        if direction in (RelationDirection.OUTGOING, RelationDirection.BOTH):
            # Check labels on this issue for outgoing relations
            try:
                labels = await self.client.get(f"{self._repo_path}/issues/{task_id}/labels")
            except Exception:
                labels = []

            for lbl in labels:
                name = lbl["name"]
                if name.startswith("rel:"):
                    parts = name.split(":")
                    if len(parts) >= 3:
                        rt_str = parts[1]
                        target = parts[2].lstrip("#")
                        try:
                            rt = RelationType(rt_str)
                        except ValueError:
                            continue
                        if relation_type is not None and rt != relation_type:
                            continue
                        relations.append(
                            Relation(
                                source_id=task_id,
                                target_id=target,
                                relation_type=rt,
                            )
                        )

        if direction in (RelationDirection.INCOMING, RelationDirection.BOTH):
            # Search all issues for labels pointing to this task
            # This is expensive but necessary for incoming relations
            for rt in [relation_type] if relation_type else list(RelationType):
                label = f"rel:{rt.value}:#{task_id}"
                try:
                    items = await self.client.get_paginated(
                        f"{self._repo_path}/issues",
                        params={"labels": label, "state": "all"},
                    )
                except Exception:
                    items = []

                for item in items:
                    if "pull_request" not in item:
                        source = str(item["number"])
                        if source != task_id:  # Avoid self-relations in BOTH mode
                            rel = Relation(
                                source_id=source,
                                target_id=task_id,
                                relation_type=rt,
                            )
                            if rel not in relations:
                                relations.append(rel)

        return relations

    async def add_relations(self, relations: list[Relation]) -> None:
        for rel in relations:
            await self.add_relation(rel.source_id, rel.target_id, RelationType(rel.relation_type))

    async def remove_relations(self, relations: list[Relation]) -> None:
        for rel in relations:
            await self.remove_relation(rel.source_id, rel.target_id, RelationType(rel.relation_type))
