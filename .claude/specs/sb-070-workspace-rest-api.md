---
title: "SB-070: Workspace REST API"
date: 2026-03-25
status: draft
issue: "#167 (SB-070)"
epic: EP-011
depends_on: [sb-069-workspace-manager]
---

# SB-070: Workspace REST API

## Goal

Create a thin organism-layer router that delegates to WorkspaceManager for cloud lifecycle operations, proxies requests to workspace servers, and manages worktrees. No business logic in the router -- pure delegation + HTTP error translation.

## Context

- **WorkspaceManager** (`molecules/services/workspace_manager.py`) handles all cloud lifecycle: `provision`, `teardown`, `stop`, `get_status`.
- **WorkspaceService** (`features/workspaces/service.py`) handles CRUD: `create`, `get`, `list_by_project`, `list_ready`, etc.
- **GCPClient** (`molecules/services/gcp_client.py`) provides `GCPClientProtocol` for mocking.
- **Existing router pattern**: see `organisms/api/routers/projects.py` -- module-level service instantiation, `DatabaseSession` dependency, `HTTPException` for errors, `model_validate` on responses.
- **Existing dependencies**: `organisms/api/dependencies.py` has `DatabaseSession`, `get_db`, `CurrentUser`, and typed DI factories for molecules.

## Endpoint Design

The app registers routers with `prefix="/api/v1"`, so the router itself uses **no prefix** -- only `tags=["workspaces"]`.

### Lifecycle Endpoints

| Method | Path | Handler | Delegates To | Status |
|--------|------|---------|-------------|--------|
| `POST` | `/projects/{project_id}/workspaces` | `create_workspace` | `WorkspaceService.create` | 201 |
| `GET` | `/projects/{project_id}/workspaces` | `list_project_workspaces` | `WorkspaceService.list_by_project` | 200 |
| `GET` | `/workspaces/{workspace_id}` | `get_workspace` | `WorkspaceService.get` | 200 |
| `DELETE` | `/workspaces/{workspace_id}` | `delete_workspace` | `WorkspaceManager.teardown` | 200 |
| `POST` | `/workspaces/{workspace_id}/provision` | `provision_workspace` | `WorkspaceManager.provision` | 200 |
| `POST` | `/workspaces/{workspace_id}/stop` | `stop_workspace` | `WorkspaceManager.stop` | 200 |
| `GET` | `/workspaces/{workspace_id}/status` | `get_workspace_status` | `WorkspaceManager.get_status` | 200 |

### Proxy Endpoint

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| `*` (any) | `/workspaces/{workspace_id}/proxy/{path:path}` | `proxy_to_workspace` | Forward to `cloud_run_url/{path}` |

### Worktree Endpoints (Convenience Proxies)

| Method | Path | Handler | Proxies To |
|--------|------|---------|------------|
| `GET` | `/workspaces/{workspace_id}/worktrees` | `list_worktrees` | `GET /worktrees` |
| `POST` | `/workspaces/{workspace_id}/worktrees` | `create_worktree` | `POST /worktrees` |
| `DELETE` | `/workspaces/{workspace_id}/worktrees/{name}` | `delete_worktree` | `DELETE /worktrees/{name}` |

## Router Implementation

### File: `app/backend/src/organisms/api/routers/workspaces.py`

```python
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response

from features.workspaces import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceService,
    WorkspaceSummary,
)
from molecules.exceptions import (
    WorkspaceNotFoundError,
    WorkspaceProvisionError,
)
from molecules.services.gcp_client import GCPClient
from molecules.services.workspace_manager import WorkspaceManager
from organisms.api.dependencies import DatabaseSession

router = APIRouter(tags=["workspaces"])

workspace_service = WorkspaceService()
```

### Dependency: WorkspaceManager Factory

Add to `organisms/api/dependencies.py`:

```python
from molecules.services.gcp_client import GCPClient, GCPClientProtocol
from molecules.services.workspace_manager import WorkspaceManager


def get_gcp_client() -> GCPClientProtocol:
    settings = get_settings()
    return GCPClient(project_id=settings.GCP_PROJECT_ID)


GCPClientDep = Annotated[GCPClientProtocol, Depends(get_gcp_client)]


def get_workspace_manager(db: DatabaseSession, gcp_client: GCPClientDep) -> WorkspaceManager:
    return WorkspaceManager(db=db, gcp_client=gcp_client)


WorkspaceManagerDep = Annotated[WorkspaceManager, Depends(get_workspace_manager)]
```

This follows the exact same pattern as `get_stack_api(db, github)` -> `StackAPIDep`.

### Endpoint Signatures

#### Create Workspace

```python
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
```

Mirrors the existing `create_workspace` in `projects.py` router. The `project_id` from the URL overrides the body field.

#### List Project Workspaces

```python
@router.get("/projects/{project_id}/workspaces", response_model=list[WorkspaceSummary])
async def list_project_workspaces(
    project_id: UUID,
    db: DatabaseSession,
    active_only: bool = Query(True),
) -> list[WorkspaceSummary]:
    items = await workspace_service.list_by_project(db, project_id, active_only=active_only)
    return [WorkspaceSummary.model_validate(w) for w in items]
```

Returns `WorkspaceSummary` (lightweight) instead of full `WorkspaceResponse` for list endpoints.

#### Get Workspace

```python
@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    db: DatabaseSession,
) -> WorkspaceResponse:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse.model_validate(workspace)
```

#### Delete Workspace (Teardown)

```python
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
```

Uses `DELETE` with a response body (the final workspace state). The `preserve_storage` query param defaults to `True` (safe default -- keep GCS bucket).

#### Provision Workspace

```python
@router.post("/workspaces/{workspace_id}/provision", response_model=WorkspaceResponse)
async def provision_workspace(
    workspace_id: UUID,
    db: DatabaseSession,
    manager: WorkspaceManagerDep,
) -> WorkspaceResponse:
    workspace = await manager.provision(workspace_id)
    await db.commit()
    return WorkspaceResponse.model_validate(workspace)
```

#### Stop Workspace

```python
@router.post("/workspaces/{workspace_id}/stop", response_model=WorkspaceResponse)
async def stop_workspace(
    workspace_id: UUID,
    db: DatabaseSession,
    manager: WorkspaceManagerDep,
) -> WorkspaceResponse:
    workspace = await manager.stop(workspace_id)
    await db.commit()
    return WorkspaceResponse.model_validate(workspace)
```

#### Get Workspace Status

```python
@router.get("/workspaces/{workspace_id}/status")
async def get_workspace_status(
    workspace_id: UUID,
    manager: WorkspaceManagerDep,
) -> dict:
    return await manager.get_status(workspace_id)
```

Returns the raw dict from `WorkspaceManager.get_status()` which includes live cloud status.

#### Proxy to Workspace

```python
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
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Cannot reach workspace server")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Workspace server timeout")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )
```

Key decisions:
- Uses `httpx.AsyncClient` for non-blocking proxy.
- Strips hop-by-hop headers before forwarding.
- Validates workspace is in `ready` state and has a `cloud_run_url`.
- Returns 502 for connection errors, 504 for timeouts.
- 30-second timeout is generous for workspace operations (file I/O, git ops).

#### Worktree Convenience Endpoints

These are thin wrappers that proxy to the workspace server's worktree API. They share a helper:

```python
async def _proxy_workspace_request(
    workspace_id: UUID,
    path: str,
    method: str,
    db: AsyncSession,
    body: bytes = b"",
    headers: dict | None = None,
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
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Cannot reach workspace server")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Workspace server timeout")

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
```

## Error Handling

### Exception-to-HTTP Mapping

Add workspace exceptions to `organisms/api/error_handlers.py`:

```python
# Add to EXCEPTION_MAP:
from molecules.exceptions import WorkspaceNotFoundError, WorkspaceProvisionError

EXCEPTION_MAP: dict[type[MoleculeError], tuple[int, str]] = {
    # ... existing entries ...
    WorkspaceNotFoundError: (404, "Workspace not found"),
    WorkspaceProvisionError: (409, "Workspace provisioning failed"),
}
```

This means `WorkspaceNotFoundError` raised by `WorkspaceManager._get_workspace()` is automatically handled by the existing `molecule_exception_handler` -- the router does NOT need try/except for those.

### State Transition Errors

`EventPattern.transition_to()` raises `InvalidStateTransitionError` when the transition is not allowed (e.g., trying to provision a workspace that's already `ready`). This needs handling:

The `WorkspaceManager` methods call `transition_to()` internally. If the transition is invalid, the exception propagates up. The router should let these propagate to a handler.

Add to `error_handlers.py`:

```python
from pattern_stack.atoms.patterns import InvalidStateTransitionError

# Add a dedicated handler in create_app():
app.add_exception_handler(InvalidStateTransitionError, state_transition_handler)

async def state_transition_handler(request: Request, exc: InvalidStateTransitionError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})
```

Alternatively, since `InvalidStateTransitionError` is NOT a `MoleculeError`, it needs its own handler or the router wraps it. The handler approach is cleaner -- a single place for all 409 state conflicts.

### Error Summary

| Error | HTTP Status | Source |
|-------|-------------|--------|
| Workspace not found | 404 | `WorkspaceNotFoundError` via `molecule_exception_handler` |
| Invalid state transition | 409 | `InvalidStateTransitionError` via new handler |
| Provision failed (GCP error) | 409 | `WorkspaceProvisionError` via `molecule_exception_handler` |
| Workspace not ready for proxy | 409 | `HTTPException` in router |
| Proxy connection failed | 502 | `HTTPException` in router |
| Proxy timeout | 504 | `HTTPException` in router |

## Router Registration

### Edit `app/backend/src/organisms/api/routers/__init__.py`

Currently empty. No changes needed (routers are imported directly in `app.py`).

### Edit `app/backend/src/organisms/api/app.py`

Add at top with other imports:

```python
from organisms.api.routers.workspaces import router as workspaces_router
```

Add in `create_app()` after the existing `include_router` calls:

```python
app.include_router(workspaces_router, prefix="/api/v1")
```

**Important:** The existing `projects.py` router already has workspace sub-routes under `/projects/{id}/workspaces`. The new workspaces router adds **non-overlapping** routes:
- `projects.py` has: `POST/GET /projects/{id}/workspaces`, `GET/PATCH/DELETE /projects/{id}/workspaces/{id}`
- New router has: `GET /workspaces/{id}` (top-level), `POST .../provision`, `POST .../stop`, `DELETE /workspaces/{id}` (teardown), proxy, worktrees

The `POST /projects/{project_id}/workspaces` and `GET /projects/{project_id}/workspaces` endpoints in the new router will **conflict** with the existing ones in `projects.py`. Resolution: **remove the duplicate workspace sub-routes from projects.py** and let the new workspaces router own all workspace endpoints. The `projects.py` router should only handle project CRUD.

Specifically, remove from `projects.py`:
- `create_workspace` (POST `/{project_id}/workspaces`)
- `list_workspaces` (GET `/{project_id}/workspaces`)
- `get_workspace` (GET `/{project_id}/workspaces/{workspace_id}`)
- `update_workspace` (PATCH `/{project_id}/workspaces/{workspace_id}`)
- `delete_workspace` (DELETE `/{project_id}/workspaces/{workspace_id}`)

And add to the new workspaces router:
- `update_workspace` (PATCH `/workspaces/{workspace_id}`) -- currently missing from the epic spec but needed for completeness.

## Request/Response Schemas

### Existing Schemas (No Changes Needed)

- `WorkspaceCreate` -- already has `project_id`, `name`, `repo_url`, `provider`, `resource_profile`, `region`, `config`
- `WorkspaceUpdate` -- already has all updatable fields
- `WorkspaceResponse` -- already has `state`, `cloud_run_url`, `gcs_bucket`, `resource_profile`, `region`, etc.
- `WorkspaceSummary` -- already has `id`, `name`, `state`, `resource_profile`, `cloud_run_url`

### New Schema: TeardownRequest (Optional)

Not needed -- `preserve_storage` is a query parameter on DELETE.

### New Schema: WorkspaceStatusResponse (Optional)

The `get_status` endpoint returns `WorkspaceManager.get_status()` which is a plain dict. For better API docs, define a response schema:

```python
# Add to features/workspaces/schemas/output.py

class WorkspaceStatusResponse(BaseModel):
    workspace_id: str
    state: str
    resource_profile: str
    region: str
    cloud_run_service: str | None = None
    cloud_run_url: str | None = None
    gcs_bucket: str | None = None
    cloud_run_status: str | None = None
    cloud_run_revision: str | None = None
    bucket_exists: bool | None = None
```

Update the endpoint to use `response_model=WorkspaceStatusResponse`.

## Dependency: httpx

Add `httpx` to `pyproject.toml` dependencies. Check if it's already present (FastAPI's test client uses it, but it may not be a direct dependency).

```bash
# Check current dependencies
grep httpx app/backend/pyproject.toml
```

If not present, add: `httpx>=0.27.0` to `[project.dependencies]`.

## Test Plan

### File: `app/backend/__tests__/organisms/test_workspace_routers.py`

Uses the `client` and `db` fixtures from conftest.py. WorkspaceManager is tested via mocking (the router tests should NOT call real GCP).

#### Strategy

- **Lifecycle endpoints**: Create workspace via DB, then test each endpoint.
- **Manager endpoints** (provision, stop, teardown): Mock `WorkspaceManager` via dependency override.
- **Proxy endpoint**: Mock `httpx.AsyncClient` to avoid real HTTP calls.
- **Worktree endpoints**: Same mock strategy as proxy.
- **Error cases**: Test 404, 409, 502, 504 responses.

#### Test Names

```python
# --- Route Registration ---

@pytest.mark.unit
async def test_workspace_routes_registered():
    """Verify workspace routes are registered on the app."""

# --- Create ---

@pytest.mark.integration
async def test_create_workspace(client, db):
    """POST /projects/{id}/workspaces creates workspace with 201."""

@pytest.mark.integration
async def test_create_workspace_sets_project_id_from_url(client, db):
    """project_id in URL overrides any project_id in body."""

# --- List ---

@pytest.mark.integration
async def test_list_project_workspaces(client, db):
    """GET /projects/{id}/workspaces returns workspace summaries."""

@pytest.mark.integration
async def test_list_project_workspaces_active_only(client, db):
    """active_only=true filters inactive workspaces."""

# --- Get ---

@pytest.mark.integration
async def test_get_workspace(client, db):
    """GET /workspaces/{id} returns full workspace response."""

@pytest.mark.integration
async def test_get_workspace_not_found(client):
    """GET /workspaces/{unknown_id} returns 404."""

# --- Delete (Teardown) ---

@pytest.mark.integration
async def test_delete_workspace_teardown(client, db):
    """DELETE /workspaces/{id} delegates to manager.teardown."""

@pytest.mark.integration
async def test_delete_workspace_preserve_storage_default(client, db):
    """preserve_storage defaults to True."""

# --- Provision ---

@pytest.mark.integration
async def test_provision_workspace(client, db):
    """POST /workspaces/{id}/provision transitions to ready."""

@pytest.mark.integration
async def test_provision_workspace_invalid_state(client, db):
    """Provisioning a 'ready' workspace returns 409."""

@pytest.mark.integration
async def test_provision_workspace_not_found(client):
    """Provisioning unknown workspace returns 404."""

# --- Stop ---

@pytest.mark.integration
async def test_stop_workspace(client, db):
    """POST /workspaces/{id}/stop transitions to stopped."""

@pytest.mark.integration
async def test_stop_workspace_invalid_state(client, db):
    """Stopping a 'created' workspace returns 409."""

# --- Status ---

@pytest.mark.integration
async def test_get_workspace_status(client, db):
    """GET /workspaces/{id}/status returns live cloud status."""

# --- Proxy ---

@pytest.mark.integration
async def test_proxy_forwards_get(client, db):
    """Proxy forwards GET to workspace cloud_run_url."""

@pytest.mark.integration
async def test_proxy_forwards_post_with_body(client, db):
    """Proxy forwards POST with request body."""

@pytest.mark.integration
async def test_proxy_workspace_not_provisioned(client, db):
    """Proxy returns 409 when workspace has no cloud_run_url."""

@pytest.mark.integration
async def test_proxy_workspace_not_ready(client, db):
    """Proxy returns 409 when workspace state is not 'ready'."""

@pytest.mark.integration
async def test_proxy_connection_error(client, db):
    """Proxy returns 502 on connection failure."""

@pytest.mark.integration
async def test_proxy_timeout(client, db):
    """Proxy returns 504 on timeout."""

# --- Worktrees ---

@pytest.mark.integration
async def test_list_worktrees(client, db):
    """GET /workspaces/{id}/worktrees proxies to workspace server."""

@pytest.mark.integration
async def test_create_worktree(client, db):
    """POST /workspaces/{id}/worktrees proxies with body."""

@pytest.mark.integration
async def test_delete_worktree(client, db):
    """DELETE /workspaces/{id}/worktrees/{name} proxies delete."""

@pytest.mark.integration
async def test_worktree_workspace_not_ready(client, db):
    """Worktree endpoints return 409 when workspace not ready."""
```

#### Mock Strategy for Manager Tests

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_gcp_client():
    """Mock GCPClient for dependency override."""
    client = AsyncMock()
    # Default happy-path returns
    client.create_gcs_bucket.return_value = GCSBucketInfo(name="test-bucket", location="us-east1")
    client.deploy_cloud_run_service.return_value = CloudRunServiceInfo(
        name="ws-test1234", url="https://ws-test1234.run.app", region="us-east1", status="READY"
    )
    client.bucket_exists.return_value = False
    client.get_cloud_run_service.return_value = CloudRunServiceInfo(
        name="ws-test1234", url="https://ws-test1234.run.app", region="us-east1", status="READY"
    )
    return client

@pytest.fixture
def app_with_mock_gcp(app, mock_gcp_client):
    """Override GCP client dependency."""
    from organisms.api.dependencies import get_gcp_client
    app.dependency_overrides[get_gcp_client] = lambda: mock_gcp_client
    yield app
    app.dependency_overrides.pop(get_gcp_client, None)

@pytest.fixture
def managed_client(app_with_mock_gcp):
    """Test client with mocked GCP."""
    with TestClient(app_with_mock_gcp) as c:
        yield c
```

#### Mock Strategy for Proxy Tests

```python
@pytest.fixture
def mock_httpx():
    """Patch httpx.AsyncClient for proxy tests."""
    with patch("organisms.api.routers.workspaces.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_client
```

## File List and Implementation Order

| Order | File | Action | Description |
|-------|------|--------|-------------|
| 1 | `app/backend/src/organisms/api/dependencies.py` | Edit | Add `get_gcp_client`, `GCPClientDep`, `get_workspace_manager`, `WorkspaceManagerDep` |
| 2 | `app/backend/src/features/workspaces/schemas/output.py` | Edit | Add `WorkspaceStatusResponse` schema |
| 3 | `app/backend/src/features/workspaces/__init__.py` | Edit | Export `WorkspaceStatusResponse` |
| 4 | `app/backend/src/organisms/api/routers/workspaces.py` | New | Full router: lifecycle, proxy, worktree endpoints |
| 5 | `app/backend/src/organisms/api/routers/projects.py` | Edit | Remove workspace sub-routes (lines 73-131), keep only project CRUD |
| 6 | `app/backend/src/organisms/api/error_handlers.py` | Edit | Add `WorkspaceNotFoundError`, `WorkspaceProvisionError` to `EXCEPTION_MAP`; add `InvalidStateTransitionError` handler |
| 7 | `app/backend/src/organisms/api/app.py` | Edit | Import and register `workspaces_router`; add `InvalidStateTransitionError` handler |
| 8 | `app/backend/__tests__/organisms/test_workspace_routers.py` | New | Full test suite (26 tests) |
| 9 | `app/backend/pyproject.toml` | Edit (if needed) | Ensure `httpx` is a direct dependency |

## Implementation Notes

1. **Commit pattern**: Organisms commit, molecules flush. The router calls `await db.commit()` after every `WorkspaceManager` method that mutates state. The manager only uses `flush()` internally.

2. **No auth yet**: The workspace endpoints do not require authentication in this phase. Auth will be added when user-scoped workspaces are implemented. Match the existing pattern where `projects.py` endpoints don't use `CurrentUser`.

3. **httpx import**: Import at module level (`import httpx`), not inside functions. The proxy is a core feature, not optional.

4. **Response headers from proxy**: Forward all response headers from the workspace server except hop-by-hop headers. The `Response(headers=dict(resp.headers))` is sufficient -- FastAPI handles the rest.

5. **No prefix on router**: The router uses `APIRouter(tags=["workspaces"])` with no `prefix` argument. The app adds `/api/v1` when including the router. This matches the epic spec.

6. **projects.py cleanup**: Removing workspace sub-routes from `projects.py` is a breaking change for any frontend code that uses `GET /api/v1/projects/{id}/workspaces/{workspace_id}`. The new equivalent is `GET /api/v1/workspaces/{workspace_id}` (no project scoping on get-by-id). The `POST` and `GET` list endpoints keep the same path under the new router.

## Quality Gates

```bash
just quality   # Format + lint + typecheck + test
just test      # Run pytest
```

All 26 new tests should pass. Existing `test_project_routers.py` tests may need updating if they check for workspace sub-routes on the projects router.
