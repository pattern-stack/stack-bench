"""Tests for workspace REST API router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from organisms.api.app import app as live_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_owner_id = uuid4()


async def _create_user(db):
    """Create a user for FK constraints."""
    from pattern_stack.features.users.models import User

    user = User(
        first_name="Test",
        last_name="User",
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_project(db):
    """Create a project with required fields for tests."""
    from features.projects import ProjectCreate, ProjectService

    user = await _create_user(db)
    project_service = ProjectService()
    project = await project_service.create(
        db,
        ProjectCreate(
            name=f"test-project-{uuid4().hex[:8]}",
            owner_id=user.id,
            github_repo="https://github.com/test-org/test-repo",
        ),
    )
    await db.flush()
    return project


async def _create_workspace(db, project_id, name="test-ws", *, state="created", cloud_run_url=None, cloud_run_service=None, gcs_bucket=None):
    """Create a workspace with optional state transitions."""
    from features.workspaces import WorkspaceCreate, WorkspaceService

    ws_service = WorkspaceService()
    ws = await ws_service.create(
        db,
        WorkspaceCreate(
            project_id=project_id,
            name=name,
            repo_url="https://github.com/test/repo",
            provider="github",
        ),
    )

    if state in ("provisioning", "ready", "stopped"):
        ws.transition_to("provisioning")
    if state in ("ready", "stopped"):
        ws.transition_to("ready")
    if state == "stopped":
        ws.transition_to("stopped")

    if cloud_run_url:
        ws.cloud_run_url = cloud_run_url
    if cloud_run_service:
        ws.cloud_run_service = cloud_run_service
    if gcs_bucket:
        ws.gcs_bucket = gcs_bucket

    await db.flush()
    return ws


# ---------------------------------------------------------------------------
# Route Registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_workspace_routes_registered() -> None:
    """Verify workspace routes are registered on the app."""
    routes = [getattr(r, "path", str(r)) for r in live_app.routes]
    assert any("/workspaces" in r for r in routes)
    assert any("/workspaces/{workspace_id}/provision" in r for r in routes)
    assert any("/workspaces/{workspace_id}/stop" in r for r in routes)
    assert any("/workspaces/{workspace_id}/status" in r for r in routes)
    assert any("/workspaces/{workspace_id}/proxy" in r for r in routes)
    assert any("/workspaces/{workspace_id}/worktrees" in r for r in routes)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_create_workspace(client, db) -> None:
    """POST /projects/{id}/workspaces creates workspace with 201."""
    project = await _create_project(db)
    await db.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/workspaces",
        json={
            "project_id": str(uuid4()),  # should be overridden by URL
            "name": "my-workspace",
            "repo_url": "https://github.com/test/repo",
            "provider": "github",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "my-workspace"
    assert data["project_id"] == str(project.id)
    assert data["state"] == "created"


@pytest.mark.integration
async def test_create_workspace_sets_project_id_from_url(client, db) -> None:
    """project_id in URL overrides any project_id in body."""
    project = await _create_project(db)
    await db.commit()

    body_project_id = str(uuid4())
    response = client.post(
        f"/api/v1/projects/{project.id}/workspaces",
        json={
            "project_id": body_project_id,
            "name": "override-test",
            "repo_url": "https://github.com/test/repo2",
            "provider": "github",
        },
    )
    assert response.status_code == 201
    assert response.json()["project_id"] == str(project.id)
    assert response.json()["project_id"] != body_project_id


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_list_project_workspaces(client, db) -> None:
    """GET /projects/{id}/workspaces returns workspace summaries."""
    project = await _create_project(db)
    await _create_workspace(db, project.id, name="ws-1")
    await _create_workspace(db, project.id, name="ws-2")
    await db.commit()

    response = client.get(f"/api/v1/projects/{project.id}/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert "name" in data[0]
    assert "state" in data[0]


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_workspace(client, db) -> None:
    """GET /workspaces/{id} returns full workspace response."""
    project = await _create_project(db)
    ws = await _create_workspace(db, project.id, name="get-ws")
    await db.commit()

    response = client.get(f"/api/v1/workspaces/{ws.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(ws.id)
    assert data["name"] == "get-ws"
    assert "created_at" in data
    assert "config" in data


@pytest.mark.integration
async def test_get_workspace_not_found(client) -> None:
    """GET /workspaces/{unknown_id} returns 404."""
    response = client.get(f"/api/v1/workspaces/{uuid4()}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_update_workspace(client, db) -> None:
    """PATCH /workspaces/{id} updates workspace fields."""
    project = await _create_project(db)
    ws = await _create_workspace(db, project.id, name="before-update")
    await db.commit()

    response = client.patch(
        f"/api/v1/workspaces/{ws.id}",
        json={"name": "after-update"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "after-update"


# ---------------------------------------------------------------------------
# Delete (Teardown) -- mocked manager
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_delete_workspace_teardown(client, app, db) -> None:
    """DELETE /workspaces/{id} delegates to manager.teardown."""
    from organisms.api.dependencies import get_gcp_client

    mock_gcp = AsyncMock()
    mock_gcp.delete_cloud_run_service = AsyncMock()
    mock_gcp.delete_gcs_bucket = AsyncMock()
    app.dependency_overrides[get_gcp_client] = lambda: mock_gcp

    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="teardown-ws",
        state="ready", cloud_run_service="ws-test", cloud_run_url="https://ws-test.run.app",
    )
    await db.commit()

    response = client.delete(f"/api/v1/workspaces/{ws.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "destroyed"


@pytest.mark.integration
async def test_delete_workspace_not_found(client, app) -> None:
    """DELETE /workspaces/{unknown} returns 404 via exception handler."""
    from organisms.api.dependencies import get_gcp_client

    mock_gcp = AsyncMock()
    app.dependency_overrides[get_gcp_client] = lambda: mock_gcp

    response = client.delete(f"/api/v1/workspaces/{uuid4()}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Provision -- mocked GCP
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_provision_workspace(client, app, db) -> None:
    """POST /workspaces/{id}/provision transitions to ready."""
    from organisms.api.dependencies import get_gcp_client

    from molecules.services.gcp_client import CloudRunServiceInfo, GCSBucketInfo

    mock_gcp = AsyncMock()
    mock_gcp.bucket_exists.return_value = False
    mock_gcp.create_gcs_bucket.return_value = GCSBucketInfo(
        name="test-bucket", location="northamerica-northeast2"
    )
    mock_gcp.deploy_cloud_run_service.return_value = CloudRunServiceInfo(
        name="ws-test1234",
        url="https://ws-test1234.run.app",
        region="northamerica-northeast2",
        status="READY",
    )
    app.dependency_overrides[get_gcp_client] = lambda: mock_gcp

    project = await _create_project(db)
    ws = await _create_workspace(db, project.id, name="provision-ws")
    await db.commit()

    response = client.post(f"/api/v1/workspaces/{ws.id}/provision")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "ready"
    assert data["cloud_run_url"] is not None


@pytest.mark.integration
async def test_provision_workspace_not_found(client, app) -> None:
    """Provisioning unknown workspace returns 404."""
    from organisms.api.dependencies import get_gcp_client

    mock_gcp = AsyncMock()
    app.dependency_overrides[get_gcp_client] = lambda: mock_gcp

    response = client.post(f"/api/v1/workspaces/{uuid4()}/provision")
    assert response.status_code == 404


@pytest.mark.integration
async def test_provision_workspace_invalid_state(client, app, db) -> None:
    """Provisioning a 'ready' workspace returns 409."""
    from organisms.api.dependencies import get_gcp_client

    mock_gcp = AsyncMock()
    app.dependency_overrides[get_gcp_client] = lambda: mock_gcp

    project = await _create_project(db)
    ws = await _create_workspace(db, project.id, name="prov-invalid-ws", state="ready")
    await db.commit()

    response = client.post(f"/api/v1/workspaces/{ws.id}/provision")
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Stop -- mocked GCP
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_stop_workspace(client, app, db) -> None:
    """POST /workspaces/{id}/stop transitions to stopped."""
    from organisms.api.dependencies import get_gcp_client

    mock_gcp = AsyncMock()
    mock_gcp.scale_cloud_run_service = AsyncMock()
    app.dependency_overrides[get_gcp_client] = lambda: mock_gcp

    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="stop-ws",
        state="ready", cloud_run_service="ws-stop",
    )
    await db.commit()

    response = client.post(f"/api/v1/workspaces/{ws.id}/stop")
    assert response.status_code == 200
    assert response.json()["state"] == "stopped"


@pytest.mark.integration
async def test_stop_workspace_invalid_state(client, app, db) -> None:
    """Stopping a 'created' workspace returns 409."""
    from organisms.api.dependencies import get_gcp_client

    mock_gcp = AsyncMock()
    app.dependency_overrides[get_gcp_client] = lambda: mock_gcp

    project = await _create_project(db)
    ws = await _create_workspace(db, project.id, name="stop-invalid-ws")
    await db.commit()

    response = client.post(f"/api/v1/workspaces/{ws.id}/stop")
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Status -- mocked GCP
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_workspace_status(client, app, db) -> None:
    """GET /workspaces/{id}/status returns live cloud status."""
    from organisms.api.dependencies import get_gcp_client

    from molecules.services.gcp_client import CloudRunServiceInfo

    mock_gcp = AsyncMock()
    mock_gcp.get_cloud_run_service.return_value = CloudRunServiceInfo(
        name="ws-status",
        url="https://ws-status.run.app",
        region="northamerica-northeast2",
        status="READY",
        revision="rev-1",
    )
    mock_gcp.bucket_exists.return_value = True
    app.dependency_overrides[get_gcp_client] = lambda: mock_gcp

    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="status-ws",
        state="ready",
        cloud_run_service="ws-status",
        cloud_run_url="https://ws-status.run.app",
        gcs_bucket="test-bucket",
    )
    await db.commit()

    response = client.get(f"/api/v1/workspaces/{ws.id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "ready"
    assert data["cloud_run_status"] == "READY"
    assert data["bucket_exists"] is True


# ---------------------------------------------------------------------------
# Proxy
# ---------------------------------------------------------------------------


def _mock_httpx_client(mock_response):
    """Create patched httpx.AsyncClient context manager."""
    return patch("organisms.api.routers.workspaces.httpx.AsyncClient", **{
        "return_value.__aenter__": AsyncMock(return_value=mock_response),
        "return_value.__aexit__": AsyncMock(return_value=False),
    })


def _make_mock_httpx_response(content=b'{"ok": true}', status_code=200, headers=None):
    """Build a mock httpx Response."""
    resp = MagicMock()
    resp.content = content
    resp.status_code = status_code
    resp.headers = headers or {"content-type": "application/json"}
    return resp


@pytest.mark.integration
async def test_proxy_forwards_get(client, db) -> None:
    """Proxy forwards GET to workspace cloud_run_url."""
    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="proxy-ws",
        state="ready", cloud_run_url="https://ws-proxy.run.app",
    )
    await db.commit()

    mock_resp = _make_mock_httpx_response()

    with patch("organisms.api.routers.workspaces.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.get(f"/api/v1/workspaces/{ws.id}/proxy/some/path")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        assert call_kwargs.kwargs["url"] == "https://ws-proxy.run.app/some/path"
        assert call_kwargs.kwargs["method"] == "GET"


@pytest.mark.integration
async def test_proxy_forwards_post_with_body(client, db) -> None:
    """Proxy forwards POST with request body."""
    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="proxy-post-ws",
        state="ready", cloud_run_url="https://ws-post.run.app",
    )
    await db.commit()

    mock_resp = _make_mock_httpx_response(b'{"created": true}', 201)

    with patch("organisms.api.routers.workspaces.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.post(
            f"/api/v1/workspaces/{ws.id}/proxy/api/data",
            json={"key": "value"},
        )
        assert response.status_code == 201
        mock_client.request.assert_called_once()
        assert mock_client.request.call_args.kwargs["method"] == "POST"


@pytest.mark.integration
async def test_proxy_workspace_not_provisioned(client, db) -> None:
    """Proxy returns 409 when workspace has no cloud_run_url."""
    project = await _create_project(db)
    ws = await _create_workspace(db, project.id, name="proxy-noprov-ws")
    await db.commit()

    response = client.get(f"/api/v1/workspaces/{ws.id}/proxy/test")
    assert response.status_code == 409


@pytest.mark.integration
async def test_proxy_workspace_not_ready(client, db) -> None:
    """Proxy returns 409 when workspace state is not 'ready'."""
    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="proxy-notready-ws",
        state="stopped", cloud_run_url="https://ws-stopped.run.app",
    )
    await db.commit()

    response = client.get(f"/api/v1/workspaces/{ws.id}/proxy/test")
    assert response.status_code == 409


@pytest.mark.integration
async def test_proxy_connection_error(client, db) -> None:
    """Proxy returns 502 on connection failure."""
    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="proxy-conn-ws",
        state="ready", cloud_run_url="https://ws-conn.run.app",
    )
    await db.commit()

    with patch("organisms.api.routers.workspaces.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.ConnectError("Connection refused")
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.get(f"/api/v1/workspaces/{ws.id}/proxy/test")
        assert response.status_code == 502


@pytest.mark.integration
async def test_proxy_timeout(client, db) -> None:
    """Proxy returns 504 on timeout."""
    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="proxy-timeout-ws",
        state="ready", cloud_run_url="https://ws-timeout.run.app",
    )
    await db.commit()

    with patch("organisms.api.routers.workspaces.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.ReadTimeout("Read timed out")
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.get(f"/api/v1/workspaces/{ws.id}/proxy/test")
        assert response.status_code == 504


# ---------------------------------------------------------------------------
# Worktrees
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_list_worktrees(client, db) -> None:
    """GET /workspaces/{id}/worktrees proxies to workspace server."""
    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="wt-list-ws",
        state="ready", cloud_run_url="https://ws-wt.run.app",
    )
    await db.commit()

    mock_resp = _make_mock_httpx_response(b'[{"name": "main"}]', 200)

    with patch("organisms.api.routers.workspaces.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.get(f"/api/v1/workspaces/{ws.id}/worktrees")
        assert response.status_code == 200


@pytest.mark.integration
async def test_create_worktree(client, db) -> None:
    """POST /workspaces/{id}/worktrees proxies with body."""
    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="wt-create-ws",
        state="ready", cloud_run_url="https://ws-wtc.run.app",
    )
    await db.commit()

    mock_resp = _make_mock_httpx_response(b'{"name": "feature-branch"}', 201)

    with patch("organisms.api.routers.workspaces.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.post(
            f"/api/v1/workspaces/{ws.id}/worktrees",
            json={"name": "feature-branch", "branch": "feature"},
        )
        assert response.status_code == 201


@pytest.mark.integration
async def test_delete_worktree(client, db) -> None:
    """DELETE /workspaces/{id}/worktrees/{name} proxies delete."""
    project = await _create_project(db)
    ws = await _create_workspace(
        db, project.id, name="wt-delete-ws",
        state="ready", cloud_run_url="https://ws-wtd.run.app",
    )
    await db.commit()

    mock_resp = _make_mock_httpx_response(b"", 204, headers={})

    with patch("organisms.api.routers.workspaces.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_resp
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.delete(f"/api/v1/workspaces/{ws.id}/worktrees/feature-branch")
        assert response.status_code == 204


@pytest.mark.integration
async def test_worktree_workspace_not_ready(client, db) -> None:
    """Worktree endpoints return 409 when workspace not ready."""
    project = await _create_project(db)
    ws = await _create_workspace(db, project.id, name="wt-notready-ws")
    await db.commit()

    response = client.get(f"/api/v1/workspaces/{ws.id}/worktrees")
    assert response.status_code == 409
