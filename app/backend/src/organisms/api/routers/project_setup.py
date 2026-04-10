import json
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from features.projects.service import ProjectService
from features.stacks.schemas.input import StackCreate
from features.stacks.service import StackService
from features.workspaces.service import WorkspaceService
from molecules.entities.stack_entity import StackEntity
from molecules.workflows.project_setup import ProjectSetupError, ProjectSetupWorkflow
from organisms.api.dependencies import CurrentUser, DatabaseSession

router = APIRouter(prefix="/projects", tags=["projects"])


# --- Request / Response schemas ---


class ProjectSetupRequest(BaseModel):
    name: str
    local_path: str
    description: str | None = None


class ProjectSetupResponse(BaseModel):
    project_id: str
    workspace_id: str
    project_name: str


class SyncedStackInfo(BaseModel):
    stack_id: str
    name: str
    created: bool
    branch_count: int


class SyncStacksResponse(BaseModel):
    synced: list[SyncedStackInfo]
    skipped: list[str]


# --- Endpoint ---


@router.post("/setup", response_model=ProjectSetupResponse, status_code=201)
async def setup_project(
    body: ProjectSetupRequest,
    user: CurrentUser,
    db: DatabaseSession,
) -> ProjectSetupResponse:
    """Create a project + workspace from a local git repository.

    Validates that local_path is a git repo, reads remote/branch metadata,
    and creates both entities in a single transaction.
    """
    workflow = ProjectSetupWorkflow(db)
    try:
        result = await workflow.create_local_project(
            user_id=user.id,
            name=body.name,
            local_path=body.local_path,
            description=body.description,
        )
    except ProjectSetupError as e:
        raise HTTPException(status_code=400, detail=e.message) from None

    await db.commit()

    return ProjectSetupResponse(
        project_id=str(result.project_id),
        workspace_id=str(result.workspace_id),
        project_name=result.project_name,
    )


# --- Stack sync from local CLI state ---

STACKS_DIR = Path.home() / ".claude" / "stacks"


@router.post("/{project_id}/sync-stacks", response_model=SyncStacksResponse)
async def sync_stacks_from_cli(
    project_id: UUID,
    db: DatabaseSession,
) -> SyncStacksResponse:
    """Sync stacks from the local stack CLI state file into the database.

    Reads ~/.claude/stacks/{repo_name}.json, creates or updates stacks
    and branches for the given project.
    """
    project_service = ProjectService()
    workspace_service = WorkspaceService()
    stack_service = StackService()

    # 1. Look up project and workspace
    project = await project_service.get(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace = await workspace_service.get_by_project(db, project_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="No workspace found for project")

    # 2. Derive the CLI state file path from github_repo
    repo_name = project.github_repo.rstrip("/").split("/")[-1]
    state_file = STACKS_DIR / f"{repo_name}.json"

    if not state_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No stack CLI state file found at {state_file}",
        )

    # 3. Parse the state file
    try:
        cli_state = json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=400, detail=f"Failed to read state file: {e}") from None

    stacks_data: dict[str, Any] = cli_state.get("stacks", {})
    if not stacks_data:
        return SyncStacksResponse(synced=[], skipped=[])

    # 4. Sync each stack
    entity = StackEntity(db)
    synced: list[SyncedStackInfo] = []
    skipped: list[str] = []

    for stack_name, stack_info in stacks_data.items():
        branches = stack_info.get("branches", [])
        if not branches:
            skipped.append(stack_name)
            continue

        trunk = stack_info.get("trunk", "main")

        # Create or find existing stack
        stack = await stack_service.get_by_name(db, project_id, stack_name)
        was_created = False
        if stack is None:
            stack = await stack_service.create(
                db,
                StackCreate(project_id=project_id, name=stack_name, trunk=trunk),
            )
            was_created = True

        # Build branch sync data
        branches_data = []
        for i, branch in enumerate(branches):
            branches_data.append(
                {
                    "name": branch["name"],
                    "position": i + 1,
                    "head_sha": branch.get("tip"),
                    "pr_number": branch.get("pr"),
                    "pr_url": None,
                }
            )

        # Sync branches using existing entity method
        await entity.sync_stack(stack.id, workspace.id, branches_data)

        synced.append(
            SyncedStackInfo(
                stack_id=str(stack.id),
                name=stack_name,
                created=was_created,
                branch_count=len(branches_data),
            )
        )

    await db.commit()
    return SyncStacksResponse(synced=synced, skipped=skipped)
