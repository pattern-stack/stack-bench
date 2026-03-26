"""Tests for WorkspaceManager molecule."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from molecules.exceptions import (
    WorkspaceNotFoundError,
    WorkspaceProvisionError,
)
from molecules.services.gcp_client import (
    CloudRunServiceInfo,
    GCSBucketInfo,
    ResourceProfileConfig,
)
from molecules.services.workspace_manager import WorkspaceManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_gcp_client() -> AsyncMock:
    """Create a mock GCP client implementing GCPClientProtocol."""
    client = AsyncMock()
    client.bucket_exists.return_value = False
    client.create_gcs_bucket.return_value = GCSBucketInfo(
        name="stack-bench-ws-test1234-work1234",
        location="northamerica-northeast2",
    )
    client.deploy_cloud_run_service.return_value = CloudRunServiceInfo(
        name="ws-test1234",
        url="https://ws-test1234-xyz.a.run.app",
        region="northamerica-northeast2",
        status="READY",
    )
    return client


def _make_workspace(
    *,
    state: str = "created",
    workspace_id: str | None = None,
    project_id: str | None = None,
    cloud_run_service: str | None = None,
    cloud_run_url: str | None = None,
    gcs_bucket: str | None = None,
    resource_profile: str = "standard",
    region: str = "northamerica-northeast2",
    config: dict | None = None,
) -> MagicMock:
    """Build a mock Workspace with realistic fields."""
    ws = MagicMock()
    ws.id = uuid4() if workspace_id is None else workspace_id
    ws.project_id = uuid4() if project_id is None else project_id
    ws.state = state
    ws.repo_url = "https://github.com/org/repo"
    ws.default_branch = "main"
    ws.resource_profile = resource_profile
    ws.region = region
    ws.cloud_run_service = cloud_run_service
    ws.cloud_run_url = cloud_run_url
    ws.gcs_bucket = gcs_bucket
    ws.config = config or {}

    def transition_to(new_state: str) -> None:
        ws.state = new_state

    ws.transition_to = transition_to
    return ws


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock async session."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_service_name_format() -> None:
    """_service_name returns ws-{first 8 chars}."""
    wid = uuid4()
    name = WorkspaceManager._service_name(wid)
    assert name == f"ws-{str(wid)[:8]}"
    assert name.startswith("ws-")
    assert len(name) == 11  # "ws-" + 8 chars


@pytest.mark.unit
def test_bucket_name_format() -> None:
    """_bucket_name returns stack-bench-ws-{proj[:8]}-{ws[:8]}."""
    pid = uuid4()
    wid = uuid4()
    name = WorkspaceManager._bucket_name(pid, wid)
    assert name == f"stack-bench-ws-{str(pid)[:8]}-{str(wid)[:8]}"
    assert name.startswith("stack-bench-ws-")


# ---------------------------------------------------------------------------
# _build_env_vars
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_env_vars() -> None:
    """Correct env vars built from workspace fields + config."""
    db = AsyncMock()
    gcp = AsyncMock()
    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(db, gcp)

    ws = _make_workspace(config={"CUSTOM_VAR": "custom_value", "nested": 123})
    env = manager._build_env_vars(ws, "test-bucket")

    assert env["REPO_URL"] == "https://github.com/org/repo"
    assert env["DEFAULT_BRANCH"] == "main"
    assert env["WORKSPACE_ID"] == str(ws.id)
    assert env["GCS_BUCKET"] == "test-bucket"
    assert env["CUSTOM_VAR"] == "custom_value"
    # Non-string config values are excluded
    assert "nested" not in env


@pytest.mark.unit
def test_build_env_vars_empty_config() -> None:
    """Empty config produces only base env vars."""
    db = AsyncMock()
    gcp = AsyncMock()
    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(db, gcp)

    ws = _make_workspace(config={})
    env = manager._build_env_vars(ws, "bucket")
    assert len(env) == 4  # REPO_URL, DEFAULT_BRANCH, WORKSPACE_ID, GCS_BUCKET


# ---------------------------------------------------------------------------
# ResourceProfileConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_resource_profile_configs() -> None:
    """ResourceProfileConfig.from_profile returns correct values."""
    light = ResourceProfileConfig.from_profile("light")
    assert light.cpu == "1"
    assert light.memory == "512Mi"

    standard = ResourceProfileConfig.from_profile("standard")
    assert standard.cpu == "2"
    assert standard.memory == "1Gi"

    heavy = ResourceProfileConfig.from_profile("heavy")
    assert heavy.cpu == "4"
    assert heavy.memory == "2Gi"


@pytest.mark.unit
def test_resource_profile_invalid() -> None:
    """Unknown profile raises ValueError."""
    with pytest.raises(ValueError, match="Unknown resource profile"):
        ResourceProfileConfig.from_profile("unknown")


# ---------------------------------------------------------------------------
# provision
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_provision_happy_path(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """Full provision flow: created -> provisioning -> ready."""
    ws = _make_workspace(state="created")
    with patch("molecules.services.workspace_manager.get_settings") as mock_settings:
        mock_settings.return_value.GCP_WORKSPACE_IMAGE = "test-image:latest"
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        result = await manager.provision(ws.id)

    assert result.state == "ready"
    assert result.cloud_run_service == "ws-test1234"
    assert result.cloud_run_url == "https://ws-test1234-xyz.a.run.app"
    assert result.gcs_bucket is not None

    # GCP calls made
    mock_gcp_client.bucket_exists.assert_called_once()
    mock_gcp_client.create_gcs_bucket.assert_called_once()
    mock_gcp_client.deploy_cloud_run_service.assert_called_once()

    # DB flushed at least twice (provisioning + ready)
    assert mock_db.flush.call_count >= 2


@pytest.mark.unit
async def test_provision_reprovision_from_stopped(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """Re-provisioning from stopped: bucket exists so not re-created."""
    ws = _make_workspace(state="stopped", gcs_bucket="existing-bucket")
    mock_gcp_client.bucket_exists.return_value = True

    with patch("molecules.services.workspace_manager.get_settings") as mock_settings:
        mock_settings.return_value.GCP_WORKSPACE_IMAGE = "test-image:latest"
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        result = await manager.provision(ws.id)

    assert result.state == "ready"
    # Bucket not re-created
    mock_gcp_client.create_gcs_bucket.assert_not_called()
    # Cloud Run still deployed
    mock_gcp_client.deploy_cloud_run_service.assert_called_once()


@pytest.mark.unit
async def test_provision_gcs_failure_rolls_back(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """GCS creation fails: state rolls back to created."""
    ws = _make_workspace(state="created")
    mock_gcp_client.create_gcs_bucket.side_effect = RuntimeError("GCS unavailable")

    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        with pytest.raises(WorkspaceProvisionError, match="GCS unavailable"):
            await manager.provision(ws.id)

    assert ws.state == "created"


@pytest.mark.unit
async def test_provision_cloud_run_failure_rolls_back(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """Cloud Run deploy fails: state rolls back, bucket remains."""
    ws = _make_workspace(state="created")
    mock_gcp_client.deploy_cloud_run_service.side_effect = RuntimeError("Deploy failed")

    with patch("molecules.services.workspace_manager.get_settings") as mock_settings:
        mock_settings.return_value.GCP_WORKSPACE_IMAGE = "test-image:latest"
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        with pytest.raises(WorkspaceProvisionError, match="Deploy failed"):
            await manager.provision(ws.id)

    assert ws.state == "created"
    # Bucket was created but not cleaned up (harmless, reused on retry)
    mock_gcp_client.create_gcs_bucket.assert_called_once()


@pytest.mark.unit
async def test_provision_invalid_state(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """Calling provision on a 'ready' workspace raises InvalidStateTransitionError."""
    from pattern_stack.atoms.patterns import InvalidStateTransitionError

    ws = _make_workspace(state="ready")

    # Make transition_to raise for invalid transition
    def strict_transition(new_state: str) -> None:
        valid_transitions = {
            "ready": ["stopped", "destroying"],
        }
        if new_state not in valid_transitions.get(ws.state, []):
            raise InvalidStateTransitionError(ws.state, new_state, list(valid_transitions.get(ws.state, [])))
        ws.state = new_state

    ws.transition_to = strict_transition

    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        with pytest.raises(InvalidStateTransitionError):
            await manager.provision(ws.id)


# ---------------------------------------------------------------------------
# teardown
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_teardown_happy_path(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """ready -> destroying -> destroyed, Cloud Run deleted, bucket preserved."""
    ws = _make_workspace(
        state="ready",
        cloud_run_service="ws-test1234",
        cloud_run_url="https://ws-test1234.run.app",
        gcs_bucket="stack-bench-ws-proj-work",
    )

    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        result = await manager.teardown(ws.id)

    assert result.state == "destroyed"
    assert result.cloud_run_service is None
    assert result.cloud_run_url is None
    # Bucket preserved by default
    assert result.gcs_bucket == "stack-bench-ws-proj-work"

    mock_gcp_client.delete_cloud_run_service.assert_called_once_with(
        service_name="ws-test1234",
        region="northamerica-northeast2",
    )
    mock_gcp_client.delete_gcs_bucket.assert_not_called()


@pytest.mark.unit
async def test_teardown_with_storage_deletion(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """preserve_storage=False: both Cloud Run and GCS deleted."""
    ws = _make_workspace(
        state="ready",
        cloud_run_service="ws-test1234",
        cloud_run_url="https://ws-test1234.run.app",
        gcs_bucket="stack-bench-ws-proj-work",
    )

    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        result = await manager.teardown(ws.id, preserve_storage=False)

    assert result.state == "destroyed"
    assert result.cloud_run_service is None
    assert result.gcs_bucket is None

    mock_gcp_client.delete_cloud_run_service.assert_called_once()
    mock_gcp_client.delete_gcs_bucket.assert_called_once_with("stack-bench-ws-proj-work")


@pytest.mark.unit
async def test_teardown_cloud_run_failure(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """Cloud Run delete fails: stays in 'destroying' state."""
    ws = _make_workspace(
        state="ready",
        cloud_run_service="ws-test1234",
    )
    mock_gcp_client.delete_cloud_run_service.side_effect = RuntimeError("Delete failed")

    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        with pytest.raises(WorkspaceProvisionError, match="Teardown failed"):
            await manager.teardown(ws.id)

    assert ws.state == "destroying"


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_stop_scales_to_zero(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """ready -> stopped, scale_cloud_run_service called with min=0, max=0."""
    ws = _make_workspace(
        state="ready",
        cloud_run_service="ws-test1234",
    )

    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        result = await manager.stop(ws.id)

    assert result.state == "stopped"
    mock_gcp_client.scale_cloud_run_service.assert_called_once_with(
        service_name="ws-test1234",
        region="northamerica-northeast2",
        min_instances=0,
        max_instances=0,
    )


@pytest.mark.unit
async def test_stop_no_cloud_run_service(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """Workspace without cloud_run_service: just transitions state."""
    ws = _make_workspace(state="ready", cloud_run_service=None)

    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        result = await manager.stop(ws.id)

    assert result.state == "stopped"
    mock_gcp_client.scale_cloud_run_service.assert_not_called()


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_get_status_ready(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """Returns workspace state + live cloud status."""
    ws = _make_workspace(
        state="ready",
        cloud_run_service="ws-test1234",
        cloud_run_url="https://ws-test1234.run.app",
        gcs_bucket="test-bucket",
    )
    mock_gcp_client.get_cloud_run_service.return_value = CloudRunServiceInfo(
        name="ws-test1234",
        url="https://ws-test1234.run.app",
        region="northamerica-northeast2",
        status="READY",
        revision="ws-test1234-00001",
    )
    mock_gcp_client.bucket_exists.return_value = True

    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        status = await manager.get_status(ws.id)

    assert status["state"] == "ready"
    assert status["cloud_run_status"] == "READY"
    assert status["cloud_run_revision"] == "ws-test1234-00001"
    assert status["bucket_exists"] is True
    assert status["workspace_id"] == str(ws.id)


@pytest.mark.unit
async def test_get_status_created(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """Created workspace: no cloud queries, just workspace state."""
    ws = _make_workspace(
        state="created",
        cloud_run_service=None,
        gcs_bucket=None,
    )

    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=ws)

        status = await manager.get_status(ws.id)

    assert status["state"] == "created"
    assert "cloud_run_status" not in status
    assert "bucket_exists" not in status
    mock_gcp_client.get_cloud_run_service.assert_not_called()
    mock_gcp_client.bucket_exists.assert_not_called()


# ---------------------------------------------------------------------------
# workspace not found
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_workspace_not_found(mock_db: AsyncMock, mock_gcp_client: AsyncMock) -> None:
    """Non-existent workspace_id raises WorkspaceNotFoundError."""
    with patch("molecules.services.workspace_manager.get_settings"):
        manager = WorkspaceManager(mock_db, mock_gcp_client)
        manager.workspace_service.get = AsyncMock(return_value=None)

        with pytest.raises(WorkspaceNotFoundError):
            await manager.provision(uuid4())
