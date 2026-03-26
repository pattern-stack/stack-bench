from uuid import uuid4

import pytest
from pattern_stack.atoms.patterns import InvalidStateTransitionError
from pydantic import ValidationError

from features.workspaces.models import Workspace
from features.workspaces.schemas.input import WorkspaceCreate, WorkspaceUpdate
from features.workspaces.schemas.output import WorkspaceResponse, WorkspaceSummary
from features.workspaces.service import WorkspaceService


# ---------------------------------------------------------------------------
# Existing tests (preserved)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_workspace_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(Workspace, "project_id")
    assert hasattr(Workspace, "name")
    assert hasattr(Workspace, "repo_url")
    assert hasattr(Workspace, "provider")
    assert hasattr(Workspace, "default_branch")
    assert hasattr(Workspace, "local_path")
    assert hasattr(Workspace, "metadata_")
    assert hasattr(Workspace, "is_active")


@pytest.mark.unit
def test_workspace_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert Workspace.Pattern.entity == "workspace"
    assert Workspace.Pattern.reference_prefix == "WKSP"


@pytest.mark.unit
def test_workspace_create_schema() -> None:
    """Verify create schema with minimal data."""
    data = WorkspaceCreate(
        project_id=uuid4(),
        name="backend",
        repo_url="https://github.com/org/repo",
        provider="github",
    )
    assert data.default_branch == "main"
    assert data.is_active is True


@pytest.mark.unit
def test_workspace_create_schema_full() -> None:
    """Verify create schema with all fields."""
    pid = uuid4()
    data = WorkspaceCreate(
        project_id=pid,
        name="backend",
        repo_url="https://github.com/org/repo",
        provider="gitlab",
        default_branch="develop",
        local_path="/home/user/repo",
        metadata_={"ci": True},
        is_active=False,
    )
    assert data.project_id == pid
    assert data.provider == "gitlab"
    assert data.local_path == "/home/user/repo"
    assert data.metadata_ == {"ci": True}
    assert data.is_active is False


@pytest.mark.unit
def test_workspace_create_requires_fields() -> None:
    """Verify required fields raise ValidationError when missing."""
    with pytest.raises(ValidationError):
        WorkspaceCreate(project_id=uuid4(), name="x", repo_url="http://x")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        WorkspaceCreate(project_id=uuid4(), repo_url="http://x", provider="github")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        WorkspaceCreate(project_id=uuid4(), name="x", provider="github")  # type: ignore[call-arg]


@pytest.mark.unit
def test_workspace_create_rejects_invalid_provider() -> None:
    """Verify invalid provider is rejected."""
    with pytest.raises(ValidationError):
        WorkspaceCreate(
            project_id=uuid4(),
            name="backend",
            repo_url="https://github.com/org/repo",
            provider="svn",
        )


@pytest.mark.unit
def test_workspace_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = WorkspaceUpdate(name="new-name")
    assert data.name == "new-name"
    assert data.repo_url is None


@pytest.mark.unit
def test_workspace_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert WorkspaceResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_workspace_service_model() -> None:
    """Verify service is configured with correct model."""
    service = WorkspaceService()
    assert service.model is Workspace


# ---------------------------------------------------------------------------
# New tests: EventPattern fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_workspace_model_has_event_pattern_fields() -> None:
    """Verify model has state, deleted_at, reference_number attributes."""
    assert hasattr(Workspace, "state")
    assert hasattr(Workspace, "deleted_at")
    assert hasattr(Workspace, "reference_number")


@pytest.mark.unit
def test_workspace_model_has_cloud_fields() -> None:
    """Verify model has cloud provisioning fields."""
    assert hasattr(Workspace, "resource_profile")
    assert hasattr(Workspace, "region")
    assert hasattr(Workspace, "cloud_run_service")
    assert hasattr(Workspace, "cloud_run_url")
    assert hasattr(Workspace, "gcs_bucket")
    assert hasattr(Workspace, "config")


@pytest.mark.unit
def test_workspace_pattern_config_states() -> None:
    """Verify state machine configuration."""
    assert Workspace.Pattern.initial_state == "created"
    assert len(Workspace.Pattern.states) == 6
    expected_states = {"created", "provisioning", "ready", "stopped", "destroying", "destroyed"}
    assert set(Workspace.Pattern.states.keys()) == expected_states
    assert set(Workspace.Pattern.state_phases.keys()) == expected_states


@pytest.mark.unit
def test_workspace_initial_state() -> None:
    """Create Workspace(), verify state == 'created'."""
    ws = Workspace()
    assert ws.state == "created"


@pytest.mark.unit
def test_workspace_state_transition_created_to_provisioning() -> None:
    """Transition created -> provisioning."""
    ws = Workspace()
    ws.transition_to("provisioning")
    assert ws.state == "provisioning"


@pytest.mark.unit
def test_workspace_state_transition_provisioning_to_ready() -> None:
    """Transition created -> provisioning -> ready."""
    ws = Workspace()
    ws.transition_to("provisioning")
    ws.transition_to("ready")
    assert ws.state == "ready"


@pytest.mark.unit
def test_workspace_state_transition_provisioning_fails_back_to_created() -> None:
    """Transition created -> provisioning -> created (failure case)."""
    ws = Workspace()
    ws.transition_to("provisioning")
    ws.transition_to("created")
    assert ws.state == "created"


@pytest.mark.unit
def test_workspace_state_transition_ready_to_stopped() -> None:
    """Full path: created -> provisioning -> ready -> stopped."""
    ws = Workspace()
    ws.transition_to("provisioning")
    ws.transition_to("ready")
    ws.transition_to("stopped")
    assert ws.state == "stopped"


@pytest.mark.unit
def test_workspace_state_transition_stopped_to_provisioning() -> None:
    """Re-provision: stopped -> provisioning."""
    ws = Workspace()
    ws.transition_to("provisioning")
    ws.transition_to("ready")
    ws.transition_to("stopped")
    ws.transition_to("provisioning")
    assert ws.state == "provisioning"


@pytest.mark.unit
def test_workspace_state_transition_ready_to_destroying() -> None:
    """Teardown from ready: ready -> destroying -> destroyed."""
    ws = Workspace()
    ws.transition_to("provisioning")
    ws.transition_to("ready")
    ws.transition_to("destroying")
    ws.transition_to("destroyed")
    assert ws.state == "destroyed"


@pytest.mark.unit
def test_workspace_state_transition_stopped_to_destroying() -> None:
    """Teardown from stopped: stopped -> destroying -> destroyed."""
    ws = Workspace()
    ws.transition_to("provisioning")
    ws.transition_to("ready")
    ws.transition_to("stopped")
    ws.transition_to("destroying")
    ws.transition_to("destroyed")
    assert ws.state == "destroyed"


@pytest.mark.unit
def test_workspace_full_lifecycle() -> None:
    """Complete lifecycle: created -> provisioning -> ready -> stopped -> provisioning -> ready -> destroying -> destroyed."""
    ws = Workspace()
    assert ws.state == "created"
    ws.transition_to("provisioning")
    ws.transition_to("ready")
    ws.transition_to("stopped")
    ws.transition_to("provisioning")
    ws.transition_to("ready")
    ws.transition_to("destroying")
    ws.transition_to("destroyed")
    assert ws.state == "destroyed"
    assert ws.get_allowed_transitions() == []


@pytest.mark.unit
def test_workspace_invalid_transition_created_to_ready() -> None:
    """Verify created cannot skip to ready."""
    ws = Workspace()
    with pytest.raises(InvalidStateTransitionError):
        ws.transition_to("ready")


@pytest.mark.unit
def test_workspace_invalid_transition_destroyed_to_any() -> None:
    """Verify destroyed is a terminal state."""
    ws = Workspace()
    ws.transition_to("provisioning")
    ws.transition_to("ready")
    ws.transition_to("destroying")
    ws.transition_to("destroyed")
    with pytest.raises(InvalidStateTransitionError):
        ws.transition_to("created")


@pytest.mark.unit
def test_workspace_invalid_transition_ready_to_created() -> None:
    """Verify ready cannot go back to created."""
    ws = Workspace()
    ws.transition_to("provisioning")
    ws.transition_to("ready")
    with pytest.raises(InvalidStateTransitionError):
        ws.transition_to("created")


@pytest.mark.unit
def test_workspace_can_transition_to() -> None:
    """Verify can_transition_to() returns correct booleans."""
    ws = Workspace()
    assert ws.can_transition_to("provisioning") is True
    assert ws.can_transition_to("ready") is False
    assert ws.can_transition_to("destroyed") is False


@pytest.mark.unit
def test_workspace_soft_delete() -> None:
    """Soft delete sets is_deleted."""
    ws = Workspace()
    ws.soft_delete()
    assert ws.is_deleted is True


@pytest.mark.unit
def test_workspace_restore() -> None:
    """Soft delete then restore."""
    ws = Workspace()
    ws.soft_delete()
    assert ws.is_deleted is True
    ws.restore()
    assert ws.is_deleted is False


# ---------------------------------------------------------------------------
# New tests: Schema cloud fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_workspace_create_schema_with_cloud_fields() -> None:
    """Create WorkspaceCreate with cloud fields."""
    data = WorkspaceCreate(
        project_id=uuid4(),
        name="backend",
        repo_url="https://github.com/org/repo",
        provider="github",
        resource_profile="heavy",
        region="us-central1",
        config={"gpu": True},
    )
    assert data.resource_profile == "heavy"
    assert data.region == "us-central1"
    assert data.config == {"gpu": True}


@pytest.mark.unit
def test_workspace_create_schema_defaults_cloud_fields() -> None:
    """Create WorkspaceCreate without cloud fields, verify defaults."""
    data = WorkspaceCreate(
        project_id=uuid4(),
        name="backend",
        repo_url="https://github.com/org/repo",
        provider="github",
    )
    assert data.resource_profile == "standard"
    assert data.region == "northamerica-northeast2"
    assert data.config == {}


@pytest.mark.unit
def test_workspace_create_rejects_invalid_resource_profile() -> None:
    """Verify Literal validation for resource_profile."""
    with pytest.raises(ValidationError):
        WorkspaceCreate(
            project_id=uuid4(),
            name="backend",
            repo_url="https://github.com/org/repo",
            provider="github",
            resource_profile="mega",
        )


@pytest.mark.unit
def test_workspace_update_schema_with_cloud_fields() -> None:
    """Create WorkspaceUpdate with cloud fields."""
    data = WorkspaceUpdate(resource_profile="light", config={"debug": True})
    assert data.resource_profile == "light"
    assert data.config == {"debug": True}


@pytest.mark.unit
def test_workspace_response_schema_has_cloud_fields() -> None:
    """Verify WorkspaceResponse includes state and cloud fields."""
    fields = WorkspaceResponse.model_fields
    assert "state" in fields
    assert "resource_profile" in fields
    assert "region" in fields
    assert "cloud_run_url" in fields
    assert "gcs_bucket" in fields
    assert "config" in fields
    assert "reference_number" in fields


@pytest.mark.unit
def test_workspace_summary_schema() -> None:
    """Verify WorkspaceSummary fields and config."""
    fields = WorkspaceSummary.model_fields
    assert "id" in fields
    assert "name" in fields
    assert "state" in fields
    assert "resource_profile" in fields
    assert "cloud_run_url" in fields
    assert WorkspaceSummary.model_config.get("from_attributes") is True
