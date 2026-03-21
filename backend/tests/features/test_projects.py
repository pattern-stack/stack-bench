import pytest
from pydantic import ValidationError

from features.projects.models import Project
from features.projects.schemas.input import ProjectCreate, ProjectUpdate
from features.projects.schemas.output import ProjectResponse
from features.projects.service import ProjectService


@pytest.mark.unit
def test_project_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(Project, "name")
    assert hasattr(Project, "description")
    assert hasattr(Project, "metadata_")
    assert hasattr(Project, "state")


@pytest.mark.unit
def test_project_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert Project.Pattern.entity == "project"
    assert Project.Pattern.reference_prefix == "PROJ"
    assert Project.Pattern.initial_state == "setup"
    assert "setup" in Project.Pattern.states
    assert "active" in Project.Pattern.states["setup"]


@pytest.mark.unit
def test_project_state_machine() -> None:
    """Verify state machine transitions."""
    project = Project()
    assert project.state == "setup"
    assert project.can_transition_to("active")
    project.transition_to("active")
    assert project.state == "active"
    assert project.can_transition_to("archived")


@pytest.mark.unit
def test_project_invalid_transition() -> None:
    """Verify setup cannot transition directly to archived."""
    project = Project()
    assert not project.can_transition_to("archived")


@pytest.mark.unit
def test_project_full_lifecycle() -> None:
    """Verify full lifecycle: setup -> active -> archived."""
    project = Project()
    assert project.state == "setup"
    project.transition_to("active")
    assert project.state == "active"
    project.transition_to("archived")
    assert project.state == "archived"
    assert project.get_allowed_transitions() == []


@pytest.mark.unit
def test_project_create_schema() -> None:
    """Verify create schema with minimal data."""
    data = ProjectCreate(name="my-project")
    assert data.name == "my-project"
    assert data.description is None
    assert data.metadata_ is None


@pytest.mark.unit
def test_project_create_schema_full() -> None:
    """Verify create schema with all fields."""
    data = ProjectCreate(
        name="my-project",
        description="A test project",
        metadata_={"key": "value"},
    )
    assert data.name == "my-project"
    assert data.description == "A test project"
    assert data.metadata_ == {"key": "value"}


@pytest.mark.unit
def test_project_create_requires_name() -> None:
    """Verify name is required."""
    with pytest.raises(ValidationError):
        ProjectCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_project_create_rejects_empty_name() -> None:
    """Verify empty name is rejected."""
    with pytest.raises(ValidationError):
        ProjectCreate(name="")


@pytest.mark.unit
def test_project_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = ProjectUpdate(description="new desc")
    assert data.description == "new desc"
    assert data.name is None


@pytest.mark.unit
def test_project_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert ProjectResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_project_service_model() -> None:
    """Verify service is configured with correct model."""
    service = ProjectService()
    assert service.model is Project
