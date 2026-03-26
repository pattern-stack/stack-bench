"""Workspace REST API router.

Thin organism-layer router that delegates to WorkspaceManager for cloud
lifecycle operations, proxies requests to workspace servers, and manages
worktrees. No business logic -- pure delegation + HTTP error translation.
"""

from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from features.workspaces import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceService,
    WorkspaceStatusResponse,
    WorkspaceSummary,
    WorkspaceUpdate,
)
from organisms.api.dependencies import DatabaseSession, WorkspaceManagerDep

router = APIRouter(tags=["workspaces"])

workspace_service = WorkspaceService()


# --- Lifecycle Endpoints ---


@router.post("/projects/{project_id}/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    project_id: UUID,
    data: WorkspaceCreate,
    db: DatabaseSession,
) -> WorkspaceResponse:
    create_data = data.model_copy(update={"project_id": project_id})
    workspace = await workspace_service.create(db, create_data)
    await db.commit()
    return WorkspaceResponse.model_validate(workspace)


@router.get("/projects/{project_id}/workspaces", response_model=list[WorkspaceSummary])
async def list_project_workspaces(
    project_id: UUID,
    db: DatabaseSession,
    active_only: bool = Query(True),
) -> list[WorkspaceSummary]:
    items = await workspace_service.list_by_project(db, project_id, active_only=active_only)
    return [WorkspaceSummary.model_validate(w) for w in items]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    db: DatabaseSession,
) -> WorkspaceResponse:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse.model_validate(workspace)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    data: WorkspaceUpdate,
    db: DatabaseSession,
) -> WorkspaceResponse:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    updated = await workspace_service.update(db, workspace_id, data)
    await db.commit()
    return WorkspaceResponse.model_validate(updated)


@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def delete_workspace(
    workspace_id: UUID,
    db: DatabaseSession,
    manager: WorkspaceManagerDep,
    preserve_storage: bool = Query(True),
) -> WorkspaceResponse:
    workspace = await manager.teardown(workspace_id, preserve_storage=preserve_storage)
    await db.commit()
    return WorkspaceResponse.model_validate(workspace)


@router.post("/workspaces/{workspace_id}/provision", response_model=WorkspaceResponse)
async def provision_workspace(
    workspace_id: UUID,
    db: DatabaseSession,
    manager: WorkspaceManagerDep,
) -> WorkspaceResponse:
    workspace = await manager.provision(workspace_id)
    await db.commit()
    return WorkspaceResponse.model_validate(workspace)


@router.post("/workspaces/{workspace_id}/stop", response_model=WorkspaceResponse)
async def stop_workspace(
    workspace_id: UUID,
    db: DatabaseSession,
    manager: WorkspaceManagerDep,
) -> WorkspaceResponse:
    workspace = await manager.stop(workspace_id)
    await db.commit()
    return WorkspaceResponse.model_validate(workspace)


@router.get("/workspaces/{workspace_id}/status", response_model=WorkspaceStatusResponse)
async def get_workspace_status(
    workspace_id: UUID,
    manager: WorkspaceManagerDep,
) -> dict[str, Any]:
    return await manager.get_status(workspace_id)


# --- Proxy Endpoint ---


@router.api_route(
    "/workspaces/{workspace_id}/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_to_workspace(
    workspace_id: UUID,
    path: str,
    request: Request,
    db: DatabaseSession,
) -> Response:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not workspace.cloud_run_url:
        raise HTTPException(status_code=409, detail="Workspace not provisioned")
    if workspace.state != "ready":
        raise HTTPException(
            status_code=409,
            detail=f"Workspace is {workspace.state}, must be 'ready' to proxy",
        )

    target_url = f"{workspace.cloud_run_url.rstrip('/')}/{path}"

    # Forward request body and headers
    body = await request.body()
    headers = dict(request.headers)
    # Remove hop-by-hop headers
    for h in ("host", "connection", "transfer-encoding"):
        headers.pop(h, None)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
                params=dict(request.query_params),
            )
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=502, detail="Cannot reach workspace server") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Workspace server timeout") from exc

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )


# --- Worktree Convenience Endpoints ---


async def _proxy_workspace_request(
    workspace_id: UUID,
    path: str,
    method: str,
    db: AsyncSession,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> Response:
    """Shared proxy helper for convenience endpoints."""
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not workspace.cloud_run_url or workspace.state != "ready":
        raise HTTPException(status_code=409, detail="Workspace not ready")

    target_url = f"{workspace.cloud_run_url.rstrip('/')}/{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method=method, url=target_url, content=body, headers=headers or {})
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=502, detail="Cannot reach workspace server") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Workspace server timeout") from exc

    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))


@router.get("/workspaces/{workspace_id}/worktrees")
async def list_worktrees(workspace_id: UUID, db: DatabaseSession) -> Response:
    return await _proxy_workspace_request(workspace_id, "worktrees", "GET", db)


@router.post("/workspaces/{workspace_id}/worktrees")
async def create_worktree(workspace_id: UUID, request: Request, db: DatabaseSession) -> Response:
    body = await request.body()
    return await _proxy_workspace_request(workspace_id, "worktrees", "POST", db, body=body)


@router.delete("/workspaces/{workspace_id}/worktrees/{name}")
async def delete_worktree(workspace_id: UUID, name: str, db: DatabaseSession) -> Response:
    return await _proxy_workspace_request(workspace_id, f"worktrees/{name}", "DELETE", db)
