from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from features.sprints.schemas.output import SprintResponse
from features.task_comments.schemas.output import TaskCommentResponse
from features.task_projects.schemas.output import TaskProjectResponse
from features.task_tags.schemas.output import TaskTagResponse
from features.tasks.schemas.output import TaskResponse
from organisms.api.dependencies import TaskManagementAPIDep

router = APIRouter(prefix="/tasks", tags=["tasks"])


# --- Request schemas (router-local, following stacks.py pattern) ---


class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str | None = None
    issue_type: str | None = None
    project_id: UUID | None = None
    sprint_id: UUID | None = None
    assignee_id: UUID | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    priority: str | None = None
    issue_type: str | None = None
    project_id: UUID | None = None
    sprint_id: UUID | None = None
    assignee_id: UUID | None = None


class TransitionTaskRequest(BaseModel):
    state: str = Field(..., min_length=1)


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class CreateSprintRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    project_id: UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class AddCommentRequest(BaseModel):
    body: str = Field(..., min_length=1)
    author_id: UUID | None = None
    parent_id: UUID | None = None


# --- SyncResult response model (mirrors the dataclass for JSON serialization) ---


class SyncResultResponse(BaseModel):
    created: int = 0
    updated: int = 0
    deleted: int = 0
    errors: list[str] = []


# --- Task endpoints ---


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(data: CreateTaskRequest, api: TaskManagementAPIDep) -> TaskResponse:
    return await api.create_task(
        data.title,
        project_id=data.project_id,
        description=data.description,
        priority=data.priority or "none",
        issue_type=data.issue_type or "task",
        sprint_id=data.sprint_id,
        assignee_id=data.assignee_id,
    )


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    api: TaskManagementAPIDep,
    project_id: UUID | None = Query(None),  # noqa: B008
    sprint_id: UUID | None = Query(None),  # noqa: B008
) -> list[TaskResponse]:
    return await api.list_tasks(project_id=project_id, sprint_id=sprint_id)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, api: TaskManagementAPIDep) -> TaskResponse:
    return await api.get_task(task_id)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: UUID, data: UpdateTaskRequest, api: TaskManagementAPIDep) -> TaskResponse:
    return await api.update_task(
        task_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        issue_type=data.issue_type,
        sprint_id=data.sprint_id,
        assignee_id=data.assignee_id,
    )


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: UUID, api: TaskManagementAPIDep) -> None:
    await api.delete_task(task_id)


@router.post("/{task_id}/transition", response_model=TaskResponse)
async def transition_task(task_id: UUID, data: TransitionTaskRequest, api: TaskManagementAPIDep) -> TaskResponse:
    return await api.transition_task(task_id, data.state)


# --- Project endpoints ---


@router.post("/projects", response_model=TaskProjectResponse, status_code=201)
async def create_project(data: CreateProjectRequest, api: TaskManagementAPIDep) -> TaskProjectResponse:
    return await api.create_project(data.name, description=data.description)


@router.get("/projects", response_model=list[TaskProjectResponse])
async def list_projects(api: TaskManagementAPIDep) -> list[TaskProjectResponse]:
    return await api.list_projects()


@router.get("/projects/{project_id}", response_model=TaskProjectResponse)
async def get_project(project_id: UUID, api: TaskManagementAPIDep) -> TaskProjectResponse:
    return await api.get_project(project_id)


# --- Sprint endpoints ---


@router.post("/sprints", response_model=SprintResponse, status_code=201)
async def create_sprint(data: CreateSprintRequest, api: TaskManagementAPIDep) -> SprintResponse:
    return await api.create_sprint(
        data.name,
        project_id=data.project_id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
    )


@router.get("/sprints", response_model=list[SprintResponse])
async def list_sprints(
    api: TaskManagementAPIDep,
    project_id: UUID = Query(...),  # noqa: B008
) -> list[SprintResponse]:
    return await api.list_sprints(project_id)


@router.get("/sprints/active", response_model=SprintResponse | None)
async def get_active_sprint(
    api: TaskManagementAPIDep,
    project_id: UUID = Query(...),  # noqa: B008
) -> SprintResponse | None:
    return await api.get_active_sprint(project_id)


@router.get("/sprints/{sprint_id}", response_model=SprintResponse)
async def get_sprint(sprint_id: UUID, api: TaskManagementAPIDep) -> SprintResponse:
    return await api.get_sprint(sprint_id)


# --- Comment endpoints ---


@router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=201)
async def add_comment(task_id: UUID, data: AddCommentRequest, api: TaskManagementAPIDep) -> TaskCommentResponse:
    return await api.add_comment(
        task_id,
        data.body,
        author_id=data.author_id,
        parent_id=data.parent_id,
    )


@router.get("/{task_id}/comments", response_model=list[TaskCommentResponse])
async def list_comments(task_id: UUID, api: TaskManagementAPIDep) -> list[TaskCommentResponse]:
    return await api.list_comments(task_id)


# --- Tag endpoints ---


@router.post("/{task_id}/tags/{tag_id}", status_code=204)
async def apply_tag(task_id: UUID, tag_id: UUID, api: TaskManagementAPIDep) -> None:
    await api.apply_tag(task_id, tag_id)


@router.delete("/{task_id}/tags/{tag_id}", status_code=204)
async def remove_tag(task_id: UUID, tag_id: UUID, api: TaskManagementAPIDep) -> None:
    await api.remove_tag(task_id, tag_id)


@router.get("/{task_id}/tags", response_model=list[TaskTagResponse])
async def get_task_tags(task_id: UUID, api: TaskManagementAPIDep) -> list[TaskTagResponse]:
    return await api.get_task_tags(task_id)


# --- Sync endpoints ---


@router.post("/sync", response_model=SyncResultResponse)
async def sync_tasks(api: TaskManagementAPIDep) -> SyncResultResponse:
    result = await api.sync_tasks()
    return SyncResultResponse(
        created=result.created,
        updated=result.updated,
        deleted=result.deleted,
        errors=result.errors,
    )


@router.post("/{task_id}/sync", response_model=SyncResultResponse)
async def sync_task(task_id: UUID, api: TaskManagementAPIDep) -> SyncResultResponse:
    result = await api.sync_task(task_id)
    return SyncResultResponse(
        created=result.created,
        updated=result.updated,
        deleted=result.deleted,
        errors=result.errors,
    )
