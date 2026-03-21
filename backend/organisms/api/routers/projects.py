from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from features.projects import ProjectCreate, ProjectResponse, ProjectService, ProjectUpdate
from features.workspaces import WorkspaceCreate, WorkspaceResponse, WorkspaceService, WorkspaceUpdate
from organisms.api.dependencies import DatabaseSession

router = APIRouter(prefix="/projects", tags=["projects"])

project_service = ProjectService()
workspace_service = WorkspaceService()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: DatabaseSession) -> ProjectResponse:
    project = await project_service.create(db, data)
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    db: DatabaseSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[ProjectResponse]:
    items, _total = await project_service.list(db, offset=offset, limit=limit)
    return [ProjectResponse.model_validate(p) for p in items]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: DatabaseSession) -> ProjectResponse:
    project = await project_service.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: UUID, data: ProjectUpdate, db: DatabaseSession) -> ProjectResponse:
    project = await project_service.update(db, project_id, data)
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/activate", response_model=ProjectResponse)
async def activate_project(project_id: UUID, db: DatabaseSession) -> ProjectResponse:
    project = await project_service.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.transition_to("active")
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(project_id: UUID, db: DatabaseSession) -> ProjectResponse:
    project = await project_service.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.transition_to("archived")
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, db: DatabaseSession) -> None:
    await project_service.delete(db, project_id, soft=True)
    await db.commit()


# --- Workspace sub-routes (nested under project) ---


@router.post("/{project_id}/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(project_id: UUID, data: WorkspaceCreate, db: DatabaseSession) -> WorkspaceResponse:
    # Override project_id from URL path
    create_data = data.model_copy(update={"project_id": project_id})
    workspace = await workspace_service.create(db, create_data)
    await db.commit()
    return WorkspaceResponse.model_validate(workspace)


@router.get("/{project_id}/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(
    project_id: UUID,
    db: DatabaseSession,
    active_only: bool = Query(True),
) -> list[WorkspaceResponse]:
    items = await workspace_service.list_by_project(db, project_id, active_only=active_only)
    return [WorkspaceResponse.model_validate(w) for w in items]


@router.get(
    "/{project_id}/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
)
async def get_workspace(project_id: UUID, workspace_id: UUID, db: DatabaseSession) -> WorkspaceResponse:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace or workspace.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse.model_validate(workspace)


@router.patch(
    "/{project_id}/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
)
async def update_workspace(
    project_id: UUID,
    workspace_id: UUID,
    data: WorkspaceUpdate,
    db: DatabaseSession,
) -> WorkspaceResponse:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace or workspace.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    updated = await workspace_service.update(db, workspace_id, data)
    await db.commit()
    return WorkspaceResponse.model_validate(updated)


@router.delete("/{project_id}/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(project_id: UUID, workspace_id: UUID, db: DatabaseSession) -> None:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace or workspace.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await workspace_service.delete(db, workspace_id, soft=False)
    await db.commit()
