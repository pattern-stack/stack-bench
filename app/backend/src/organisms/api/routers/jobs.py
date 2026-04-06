from uuid import UUID

from fastapi import APIRouter, Query

from features.jobs.schemas.output import JobResponse
from organisms.api.dependencies import TaskAPIDep

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    api: TaskAPIDep,
    task_id: UUID = Query(...),  # noqa: B008
) -> list[JobResponse]:
    """List jobs for a task."""
    return await api.list_jobs_for_task(task_id)


@router.get("/{job_id}")
async def get_job(job_id: UUID, api: TaskAPIDep) -> dict[str, object]:
    """Get a job with its agent runs."""
    return await api.get_job(job_id)
