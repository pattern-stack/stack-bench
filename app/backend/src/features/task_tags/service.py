from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TaskTag, task_tag_assignments
from .schemas.input import TaskTagCreate, TaskTagUpdate


class TaskTagService(BaseService[TaskTag, TaskTagCreate, TaskTagUpdate]):
    model = TaskTag

    async def list_by_group(self, db: AsyncSession, group: str) -> list[TaskTag]:
        result = await db.execute(select(TaskTag).where(TaskTag.group == group).order_by(TaskTag.name.asc()))
        return list(result.scalars().all())

    async def get_by_name(self, db: AsyncSession, name: str) -> TaskTag | None:
        result = await db.execute(select(TaskTag).where(TaskTag.name == name))
        return result.scalar_one_or_none()

    # --- Tag assignment operations ---

    async def apply_tag(self, db: AsyncSession, task_id: UUID, tag_id: UUID) -> None:
        await db.execute(insert(task_tag_assignments).values(task_id=task_id, tag_id=tag_id))

    async def remove_tag(self, db: AsyncSession, task_id: UUID, tag_id: UUID) -> None:
        await db.execute(
            delete(task_tag_assignments).where(
                task_tag_assignments.c.task_id == task_id,
                task_tag_assignments.c.tag_id == tag_id,
            )
        )

    async def get_task_tags(self, db: AsyncSession, task_id: UUID) -> list[TaskTag]:
        result = await db.execute(
            select(TaskTag)
            .join(task_tag_assignments, task_tag_assignments.c.tag_id == TaskTag.id)
            .where(task_tag_assignments.c.task_id == task_id)
            .order_by(TaskTag.name.asc())
        )
        return list(result.scalars().all())

    async def set_task_tags(self, db: AsyncSession, task_id: UUID, tag_ids: list[UUID]) -> None:
        # Remove all existing tags for this task
        await db.execute(delete(task_tag_assignments).where(task_tag_assignments.c.task_id == task_id))
        # Insert the new set
        if tag_ids:
            await db.execute(
                insert(task_tag_assignments),
                [{"task_id": task_id, "tag_id": tag_id} for tag_id in tag_ids],
            )
