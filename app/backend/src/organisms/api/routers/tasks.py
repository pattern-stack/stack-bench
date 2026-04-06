from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from pydantic import Field as PydanticField

from features.tasks.schemas.output import TaskResponse
from organisms.api.dependencies import TaskAPIDep

router = APIRouter(prefix="/tasks", tags=["tasks"])


# --- Request schemas (router-local) ---


class CreateTaskRequest(BaseModel):
    title: str = PydanticField(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str = PydanticField("none", pattern="^(critical|high|medium|low|none)$")
    issue_type: str = PydanticField("task", pattern="^(story|bug|task|spike|epic)$")
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    sprint_id: UUID | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = PydanticField(None, min_length=1, max_length=500)
    description: str | None = None
    priority: str | None = PydanticField(None, pattern="^(critical|high|medium|low|none)$")
    issue_type: str | None = PydanticField(None, pattern="^(story|bug|task|spike|epic)$")
    work_phase: str | None = PydanticField(None, pattern="^(design|build|test|deploy|review)$")
    status_category: str | None = PydanticField(None, pattern="^(todo|in_progress|done)$")
    state: str | None = PydanticField(None, pattern="^(backlog|ready|in_progress|in_review|done|cancelled)$")
    assignee_id: UUID | None = None


# --- Task endpoints ---


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(data: CreateTaskRequest, api: TaskAPIDep) -> TaskResponse:
    """Create a new task."""
    from features.tasks.schemas.input import TaskCreate

    create_data = TaskCreate(
        title=data.title,
        description=data.description,
        priority=data.priority,
        issue_type=data.issue_type,
        project_id=data.project_id,
        assignee_id=data.assignee_id,
        sprint_id=data.sprint_id,
    )
    return await api.create_task(create_data)


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    api: TaskAPIDep,
    project_id: UUID = Query(...),  # noqa: B008
) -> list[TaskResponse]:
    """List tasks by project."""
    return await api.list_tasks(project_id)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, api: TaskAPIDep) -> TaskResponse:
    """Get a single task."""
    return await api.get_task(task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: UUID, data: UpdateTaskRequest, api: TaskAPIDep) -> TaskResponse:
    """Update task fields or transition state."""
    from features.tasks.schemas.input import TaskUpdate

    update_data = TaskUpdate(**data.model_dump(exclude_unset=True))
    return await api.update_task(task_id, update_data)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: UUID, api: TaskAPIDep) -> None:
    """Soft-delete a task."""
    await api.delete_task(task_id)


@router.get("/{task_id}/detail")
async def get_task_detail(task_id: UUID, api: TaskAPIDep) -> dict[str, object]:
    """Get task with linked job, agent runs, and summary.

    Returns everything the frontend task detail view needs in one call.
    """
    return await api.get_task_detail(task_id)
