from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.workspaces.models import Workspace
from features.workspaces.schemas.input import WorkspaceCreate, WorkspaceUpdate
from features.workspaces.schemas.output import WorkspaceResponse
from features.workspaces.service import WorkspaceService


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
