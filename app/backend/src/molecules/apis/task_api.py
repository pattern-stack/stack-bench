"""API facade for the task domain.

Coordinates TaskService, JobService, and AgentRunService to provide
the unified task detail view needed by the frontend dashboard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from features.agent_runs.schemas.output import AgentRunResponse
from features.agent_runs.service import AgentRunService
from features.conversations.schemas.input import ConversationCreate
from features.conversations.service import ConversationService
from features.jobs.schemas.output import JobResponse
from features.jobs.service import JobService
from features.tasks.schemas.output import TaskResponse
from features.tasks.service import TaskService

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from features.jobs.schemas.input import JobCreate
    from features.tasks.schemas.input import TaskCreate, TaskUpdate


class TaskAPI:
    """API facade for task domain.

    Composes TaskService, JobService, and AgentRunService for the
    dashboard endpoints. Both REST and future CLI consume this.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._task_svc = TaskService()
        self._job_svc = JobService()
        self._agent_run_svc = AgentRunService()
        self._conv_svc = ConversationService()
        self._link_svc = ConversationService()

    async def create_task(self, data: TaskCreate) -> TaskResponse:
        """Create a new task."""
        task = await self._task_svc.create(self.db, data)
        await self.db.commit()
        await self.db.refresh(task)
        return TaskResponse.model_validate(task)

    async def get_task(self, task_id: UUID) -> TaskResponse:
        """Get a single task by ID."""
        task = await self._task_svc.get(self.db, task_id)
        if task is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Task not found")
        return TaskResponse.model_validate(task)

    async def list_tasks(self, project_id: UUID) -> list[TaskResponse]:
        """List tasks for a project."""
        tasks = await self._task_svc.list_by_project(self.db, project_id)
        return [TaskResponse.model_validate(t) for t in tasks]

    async def update_task(self, task_id: UUID, data: TaskUpdate) -> TaskResponse:
        """Update task fields. Handles state transitions if state is provided."""
        from features.tasks.schemas.input import TaskUpdate as TaskUpdateInput

        task = await self._task_svc.get(self.db, task_id)
        if task is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Task not found")

        # Handle state transition separately from field updates
        update_data = data.model_dump(exclude_unset=True)
        target_state = update_data.pop("state", None)

        # Apply field updates if any remain (exclude state from service update)
        if update_data:
            field_update = TaskUpdateInput(**update_data)
            task = await self._task_svc.update(self.db, task_id, field_update)

        # Apply state transition if requested
        if target_state is not None:
            task = await self._task_svc.get(self.db, task_id)
            if task is not None:
                task.transition_to(target_state)

        await self.db.commit()
        if task is not None:
            await self.db.refresh(task)
        return TaskResponse.model_validate(task)

    async def delete_task(self, task_id: UUID) -> None:
        """Soft-delete a task."""
        task = await self._task_svc.get(self.db, task_id)
        if task is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Task not found")
        await self._task_svc.delete(self.db, task_id)
        await self.db.commit()

    async def get_task_detail(self, task_id: UUID) -> dict[str, Any]:
        """Get task with linked job, agent runs, and summary.

        Returns everything the frontend task detail view needs in one call.
        """
        task = await self._task_svc.get(self.db, task_id)
        if task is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Task not found")

        # Get linked jobs (most recent first)
        jobs = await self._job_svc.list_by_task(self.db, task_id)
        latest_job = jobs[0] if jobs else None

        # Get agent runs for the latest job
        agent_runs: list[AgentRunResponse] = []
        if latest_job is not None:
            runs = await self._agent_run_svc.list_by_job(self.db, latest_job.id)
            agent_runs = [AgentRunResponse.model_validate(r) for r in runs]

        job_response = JobResponse.model_validate(latest_job) if latest_job else None

        return {
            "task": TaskResponse.model_validate(task).model_dump(),
            "job": job_response.model_dump() if job_response else None,
            "agent_runs": [r.model_dump() for r in agent_runs],
        }

    # --- Job-related methods ---

    async def list_jobs_for_task(self, task_id: UUID) -> list[JobResponse]:
        """List all jobs linked to a task."""
        jobs = await self._job_svc.list_by_task(self.db, task_id)
        return [JobResponse.model_validate(j) for j in jobs]

    async def get_job(self, job_id: UUID) -> dict[str, Any]:
        """Get a job with its agent runs."""
        job = await self._job_svc.get(self.db, job_id)
        if job is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Job not found")

        runs = await self._agent_run_svc.list_by_job(self.db, job_id)
        agent_runs = [AgentRunResponse.model_validate(r) for r in runs]

        return {
            "job": JobResponse.model_validate(job).model_dump(),
            "agent_runs": [r.model_dump() for r in agent_runs],
        }

    async def create_job_for_task(self, task_id: UUID, data: JobCreate) -> tuple[JobResponse, UUID]:
        """Create a job for a task and auto-link an execution conversation.

        Returns the job response and the conversation ID.
        """
        task = await self._task_svc.get(self.db, task_id)
        if task is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Task not found")

        # Create the job
        job = await self._job_svc.create(self.db, data)

        # Create an execution conversation
        conv = await self._conv_svc.create(
            self.db,
            ConversationCreate(
                agent_name="orchestrator",
                conversation_type="execution",
            ),
        )

        # Link conversation to task
        await self._link_svc.link_conversation(
            self.db,
            conversation_id=conv.id,
            entity_type="task",
            entity_id=task_id,
            relationship_type="execution",
        )

        # Link conversation to job
        await self._link_svc.link_conversation(
            self.db,
            conversation_id=conv.id,
            entity_type="job",
            entity_id=job.id,
            relationship_type="execution",
        )

        await self.db.commit()
        await self.db.refresh(job)
        return JobResponse.model_validate(job), conv.id
