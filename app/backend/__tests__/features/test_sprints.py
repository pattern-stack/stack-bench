from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.sprints.models import Sprint
from features.sprints.schemas.input import SprintCreate, SprintUpdate
from features.sprints.schemas.output import SprintResponse
from features.sprints.service import SprintService

# --- Model tests ---


@pytest.mark.unit
def test_sprint_model_fields() -> None:
    """Verify all domain fields, FK fields, and sync fields exist on the model class."""
    # Domain fields
    assert hasattr(Sprint, "name")
    assert hasattr(Sprint, "number")
    assert hasattr(Sprint, "description")
    assert hasattr(Sprint, "starts_at")
    assert hasattr(Sprint, "ends_at")
    # FK fields
    assert hasattr(Sprint, "project_id")
    # External sync fields
    assert hasattr(Sprint, "external_id")
    assert hasattr(Sprint, "external_url")
    assert hasattr(Sprint, "provider")
    assert hasattr(Sprint, "last_synced_at")
    # EventPattern fields
    assert hasattr(Sprint, "state")


@pytest.mark.unit
def test_sprint_pattern_config() -> None:
    """Verify Pattern inner class: entity, reference_prefix, initial_state, all state keys."""
    assert Sprint.Pattern.entity == "sprint"
    assert Sprint.Pattern.reference_prefix == "SPR"
    assert Sprint.Pattern.initial_state == "planned"
    assert "planned" in Sprint.Pattern.states
    assert "active" in Sprint.Pattern.states
    assert "completed" in Sprint.Pattern.states


@pytest.mark.unit
def test_sprint_initial_state() -> None:
    """Instantiate Sprint(), assert state is 'planned'."""
    sprint = Sprint()
    assert sprint.state == "planned"


@pytest.mark.unit
def test_sprint_state_machine_happy_path() -> None:
    """Walk planned -> active -> completed."""
    sprint = Sprint()
    assert sprint.state == "planned"

    assert sprint.can_transition_to("active")
    sprint.transition_to("active")
    assert sprint.state == "active"

    assert sprint.can_transition_to("completed")
    sprint.transition_to("completed")
    assert sprint.state == "completed"


@pytest.mark.unit
def test_sprint_invalid_transitions() -> None:
    """Verify planned cannot jump to completed directly."""
    sprint = Sprint()
    assert not sprint.can_transition_to("completed")


@pytest.mark.unit
def test_sprint_terminal_state() -> None:
    """Verify completed has no allowed transitions."""
    sprint = Sprint()
    sprint.transition_to("active")
    sprint.transition_to("completed")
    assert sprint.get_allowed_transitions() == []


@pytest.mark.unit
def test_sprint_emit_and_track() -> None:
    """Verify emit_state_transitions and track_changes are enabled."""
    assert Sprint.Pattern.emit_state_transitions is True
    assert Sprint.Pattern.track_changes is True


# --- Schema tests ---


@pytest.mark.unit
def test_sprint_create_minimal() -> None:
    """SprintCreate with only name, verify defaults."""
    data = SprintCreate(name="Sprint 1")
    assert data.name == "Sprint 1"
    assert data.provider == "local"
    assert data.description is None
    assert data.project_id is None
    assert data.starts_at is None
    assert data.ends_at is None
    assert data.number is None


@pytest.mark.unit
def test_sprint_create_full() -> None:
    """SprintCreate with all fields populated, verify round-trip."""
    from datetime import UTC, datetime

    project_id = uuid4()
    now = datetime.now(UTC)

    data = SprintCreate(
        name="Sprint 1",
        number=1,
        description="First sprint",
        starts_at=now,
        ends_at=now,
        project_id=project_id,
        external_id="GH-SPRINT-1",
        external_url="https://github.com/org/repo/milestone/1",
        provider="github",
        last_synced_at=now,
    )
    assert data.name == "Sprint 1"
    assert data.number == 1
    assert data.description == "First sprint"
    assert data.starts_at == now
    assert data.ends_at == now
    assert data.project_id == project_id
    assert data.external_id == "GH-SPRINT-1"
    assert data.external_url == "https://github.com/org/repo/milestone/1"
    assert data.provider == "github"
    assert data.last_synced_at == now


@pytest.mark.unit
def test_sprint_create_requires_name() -> None:
    """Omitting name raises ValidationError."""
    with pytest.raises(ValidationError):
        SprintCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_sprint_create_rejects_empty_name() -> None:
    """Empty string name raises ValidationError."""
    with pytest.raises(ValidationError):
        SprintCreate(name="")


@pytest.mark.unit
def test_sprint_create_rejects_invalid_provider() -> None:
    """Invalid provider value raises ValidationError."""
    with pytest.raises(ValidationError):
        SprintCreate(name="Test", provider="jira")


@pytest.mark.unit
def test_sprint_update_partial() -> None:
    """SprintUpdate with only name set, rest are None."""
    data = SprintUpdate(name="Updated sprint")
    assert data.name == "Updated sprint"
    assert data.description is None
    assert data.number is None
    assert data.starts_at is None
    assert data.ends_at is None
    assert data.project_id is None


@pytest.mark.unit
def test_sprint_response_from_attributes() -> None:
    """Verify model_config has from_attributes=True."""
    assert SprintResponse.model_config.get("from_attributes") is True


# --- Service tests ---


@pytest.mark.unit
def test_sprint_service_model() -> None:
    """Verify SprintService().model is Sprint."""
    service = SprintService()
    assert service.model is Sprint


@pytest.mark.unit
def test_sprint_service_has_custom_methods() -> None:
    """Verify SprintService has get_active_sprint and list_by_project methods."""
    service = SprintService()
    assert hasattr(service, "get_active_sprint")
    assert callable(service.get_active_sprint)
    assert hasattr(service, "list_by_project")
    assert callable(service.list_by_project)
