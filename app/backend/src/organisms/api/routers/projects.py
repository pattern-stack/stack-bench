from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from features.projects import ProjectCreate, ProjectResponse, ProjectService, ProjectUpdate
from organisms.api.dependencies import DatabaseSession

router = APIRouter(prefix="/projects", tags=["projects"])

project_service = ProjectService()


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
