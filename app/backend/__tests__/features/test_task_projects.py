from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.task_projects.models import TaskProject
from features.task_projects.schemas.input import TaskProjectCreate, TaskProjectUpdate
from features.task_projects.schemas.output import TaskProjectResponse
from features.task_projects.service import TaskProjectService

# --- Model tests ---


@pytest.mark.unit
def test_task_project_model_fields() -> None:
    """Verify all domain fields and sync fields exist on the model class."""
    # Domain fields
    assert hasattr(TaskProject, "name")
    assert hasattr(TaskProject, "description")
    assert hasattr(TaskProject, "lead_id")
    # External sync fields
    assert hasattr(TaskProject, "external_id")
    assert hasattr(TaskProject, "external_url")
    assert hasattr(TaskProject, "provider")
    assert hasattr(TaskProject, "last_synced_at")
    # EventPattern fields
    assert hasattr(TaskProject, "state")


@pytest.mark.unit
def test_task_project_pattern_config() -> None:
    """Verify Pattern inner class: entity, reference_prefix, initial_state, all state keys."""
    assert TaskProject.Pattern.entity == "task_project"
    assert TaskProject.Pattern.reference_prefix == "TPJ"
    assert TaskProject.Pattern.initial_state == "backlog"
    assert "backlog" in TaskProject.Pattern.states
    assert "planning" in TaskProject.Pattern.states
    assert "active" in TaskProject.Pattern.states
    assert "on_hold" in TaskProject.Pattern.states
    assert "completed" in TaskProject.Pattern.states
    assert "archived" in TaskProject.Pattern.states


@pytest.mark.unit
def test_task_project_initial_state() -> None:
    """Instantiate TaskProject(), assert state is 'backlog'."""
    project = TaskProject()
    assert project.state == "backlog"


@pytest.mark.unit
def test_task_project_state_machine_happy_path() -> None:
    """Walk backlog -> planning -> active -> completed -> archived."""
    project = TaskProject()
    assert project.state == "backlog"

    assert project.can_transition_to("planning")
    project.transition_to("planning")
    assert project.state == "planning"

    assert project.can_transition_to("active")
    project.transition_to("active")
    assert project.state == "active"

    assert project.can_transition_to("completed")
    project.transition_to("completed")
    assert project.state == "completed"

    assert project.can_transition_to("archived")
    project.transition_to("archived")
    assert project.state == "archived"


@pytest.mark.unit
def test_task_project_on_hold_from_active() -> None:
    """Verify active -> on_hold transition."""
    project = TaskProject()
    project.transition_to("planning")
    project.transition_to("active")
    assert project.can_transition_to("on_hold")
    project.transition_to("on_hold")
    assert project.state == "on_hold"


@pytest.mark.unit
def test_task_project_on_hold_back_to_active() -> None:
    """Verify on_hold -> active (bidirectional)."""
    project = TaskProject()
    project.transition_to("planning")
    project.transition_to("active")
    project.transition_to("on_hold")
    assert project.state == "on_hold"

    assert project.can_transition_to("active")
    project.transition_to("active")
    assert project.state == "active"


@pytest.mark.unit
def test_task_project_invalid_transitions() -> None:
    """Verify backlog cannot jump to active, completed, or archived directly."""
    project = TaskProject()
    assert not project.can_transition_to("active")
    assert not project.can_transition_to("completed")
    assert not project.can_transition_to("archived")
    assert not project.can_transition_to("on_hold")


@pytest.mark.unit
def test_task_project_terminal_state() -> None:
    """Verify archived has no allowed transitions."""
    project = TaskProject()
    project.transition_to("planning")
    project.transition_to("active")
    project.transition_to("completed")
    project.transition_to("archived")
    assert project.get_allowed_transitions() == []


# --- Schema tests ---


@pytest.mark.unit
def test_task_project_create_minimal() -> None:
    """TaskProjectCreate with only name, verify defaults."""
    data = TaskProjectCreate(name="My Project")
    assert data.name == "My Project"
    assert data.description is None
    assert data.lead_id is None
    assert data.provider == "local"
    assert data.external_id is None
    assert data.external_url is None
    assert data.last_synced_at is None


@pytest.mark.unit
def test_task_project_create_full() -> None:
    """TaskProjectCreate with all fields populated, verify round-trip."""
    from datetime import UTC, datetime

    lead_id = uuid4()
    now = datetime.now(UTC)

    data = TaskProjectCreate(
        name="Full Project",
        description="A detailed description",
        lead_id=lead_id,
        external_id="GH-PRJ-1",
        external_url="https://github.com/org/repo/projects/1",
        provider="github",
        last_synced_at=now,
    )
    assert data.name == "Full Project"
    assert data.description == "A detailed description"
    assert data.lead_id == lead_id
    assert data.external_id == "GH-PRJ-1"
    assert data.external_url == "https://github.com/org/repo/projects/1"
    assert data.provider == "github"
    assert data.last_synced_at == now


@pytest.mark.unit
def test_task_project_create_requires_name() -> None:
    """Omitting name raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskProjectCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_task_project_create_rejects_empty_name() -> None:
    """Empty string name raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskProjectCreate(name="")


@pytest.mark.unit
def test_task_project_create_rejects_invalid_provider() -> None:
    """Invalid provider value raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskProjectCreate(name="Test", provider="jira")


@pytest.mark.unit
def test_task_project_update_partial() -> None:
    """TaskProjectUpdate with only name set, rest are None."""
    data = TaskProjectUpdate(name="Updated name")
    assert data.name == "Updated name"
    assert data.description is None
    assert data.lead_id is None


@pytest.mark.unit
def test_task_project_response_from_attributes() -> None:
    """Verify model_config has from_attributes=True."""
    assert TaskProjectResponse.model_config.get("from_attributes") is True


# --- Service tests ---


@pytest.mark.unit
def test_task_project_service_model() -> None:
    """Verify TaskProjectService().model is TaskProject."""
    service = TaskProjectService()
    assert service.model is TaskProject
