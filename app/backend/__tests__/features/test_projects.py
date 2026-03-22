import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from features.projects.models import Project
from features.projects.schemas.input import ProjectCreate, ProjectUpdate
from features.projects.schemas.output import ProjectResponse
from features.projects.service import ProjectService


@pytest.fixture
def temp_git_dir():
    """Create a temporary directory for testing local_path validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


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
def test_project_create_schema(temp_git_dir) -> None:
    """Verify create schema with minimal data."""
    data = ProjectCreate(
        name="my-project",
        local_path=temp_git_dir,
        github_repo="https://github.com/user/repo",
    )
    assert data.name == "my-project"
    assert data.description is None
    assert data.metadata_ is None
    assert data.local_path == temp_git_dir
    assert data.github_repo == "https://github.com/user/repo"


@pytest.mark.unit
def test_project_create_schema_full(temp_git_dir) -> None:
    """Verify create schema with all fields."""
    data = ProjectCreate(
        name="my-project",
        description="A test project",
        metadata_={"key": "value"},
        local_path=temp_git_dir,
        github_repo="https://github.com/user/repo",
    )
    assert data.name == "my-project"
    assert data.description == "A test project"
    assert data.metadata_ == {"key": "value"}
    assert data.local_path == temp_git_dir
    assert data.github_repo == "https://github.com/user/repo"


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


# New tests for local_path and github_repo fields


@pytest.mark.unit
def test_project_model_has_local_path_field() -> None:
    """Verify Project model has local_path field."""
    assert hasattr(Project, "local_path")


@pytest.mark.unit
def test_project_model_has_github_repo_field() -> None:
    """Verify Project model has github_repo field."""
    assert hasattr(Project, "github_repo")


@pytest.mark.unit
def test_project_create_requires_local_path(temp_git_dir) -> None:
    """Verify ProjectCreate requires local_path."""
    with pytest.raises(ValidationError):
        ProjectCreate(name="x", github_repo="https://github.com/user/repo")


@pytest.mark.unit
def test_project_create_requires_github_repo(temp_git_dir) -> None:
    """Verify ProjectCreate requires github_repo."""
    with pytest.raises(ValidationError):
        ProjectCreate(name="x", local_path=temp_git_dir)


@pytest.mark.unit
def test_project_create_validates_local_path_exists() -> None:
    """Verify ProjectCreate rejects non-existent paths."""
    with pytest.raises(ValidationError) as exc_info:
        ProjectCreate(
            name="x",
            local_path="/nonexistent/path",
            github_repo="https://github.com/user/repo",
        )
    assert "does not exist" in str(exc_info.value)


@pytest.mark.unit
def test_project_create_validates_local_path_is_directory(temp_git_dir) -> None:
    """Verify ProjectCreate rejects file paths (not directories)."""
    # Create a file instead of a directory
    file_path = Path(temp_git_dir) / "test_file.txt"
    file_path.write_text("test")

    with pytest.raises(ValidationError) as exc_info:
        ProjectCreate(
            name="x",
            local_path=str(file_path),
            github_repo="https://github.com/user/repo",
        )
    assert "not a directory" in str(exc_info.value)


@pytest.mark.unit
def test_project_create_validates_github_repo_format(temp_git_dir) -> None:
    """Verify ProjectCreate rejects invalid GitHub URLs."""
    with pytest.raises(ValidationError) as exc_info:
        ProjectCreate(
            name="x",
            local_path=temp_git_dir,
            github_repo="invalid",
        )
    assert "github.com" in str(exc_info.value)


@pytest.mark.unit
def test_project_create_rejects_non_https_github_repo(temp_git_dir) -> None:
    """Verify ProjectCreate rejects non-HTTPS GitHub URLs."""
    with pytest.raises(ValidationError) as exc_info:
        ProjectCreate(
            name="x",
            local_path=temp_git_dir,
            github_repo="http://github.com/user/repo",
        )
    assert "HTTPS" in str(exc_info.value)


@pytest.mark.unit
def test_project_create_with_valid_paths(temp_git_dir) -> None:
    """Verify ProjectCreate succeeds with valid local_path and github_repo."""
    data = ProjectCreate(
        name="x",
        local_path=temp_git_dir,
        github_repo="https://github.com/user/repo",
    )
    assert data.local_path == temp_git_dir
    assert data.github_repo == "https://github.com/user/repo"


@pytest.mark.unit
def test_project_update_allows_partial_local_path(temp_git_dir) -> None:
    """Verify ProjectUpdate allows updating only local_path."""
    data = ProjectUpdate(local_path=temp_git_dir)
    assert data.local_path == temp_git_dir
    assert data.github_repo is None


@pytest.mark.unit
def test_project_update_allows_partial_github_repo() -> None:
    """Verify ProjectUpdate allows updating only github_repo."""
    data = ProjectUpdate(github_repo="https://github.com/org/newrepo")
    assert data.github_repo == "https://github.com/org/newrepo"
    assert data.local_path is None


@pytest.mark.unit
def test_project_create_rejects_empty_local_path() -> None:
    """Verify ProjectCreate rejects empty local_path."""
    with pytest.raises(ValidationError):
        ProjectCreate(
            name="x",
            local_path="",
            github_repo="https://github.com/user/repo",
        )


@pytest.mark.unit
def test_project_create_rejects_empty_github_repo(temp_git_dir) -> None:
    """Verify ProjectCreate rejects empty github_repo."""
    with pytest.raises(ValidationError):
        ProjectCreate(
            name="x",
            local_path=temp_git_dir,
            github_repo="",
        )
