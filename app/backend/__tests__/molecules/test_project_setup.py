"""Unit tests for ProjectSetupWorkflow.

All tests mock asyncio.create_subprocess_exec to simulate git commands
and mock ProjectService/WorkspaceService to avoid DB access.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from molecules.workflows.project_setup import (
    ProjectSetupError,
    ProjectSetupWorkflow,
    _detect_provider,
    _normalize_remote_url,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_process(stdout: str = "", returncode: int = 0) -> AsyncMock:
    """Create a mock subprocess that returns the given stdout/stderr."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout.encode(), b""))
    proc.returncode = returncode
    return proc


def _mock_project(project_id=None, name="test-project"):
    """Create a mock project object with transition_to."""
    proj = MagicMock()
    proj.id = project_id or uuid4()
    proj.name = name
    proj.transition_to = MagicMock()
    return proj


def _mock_workspace(workspace_id=None):
    """Create a mock workspace object."""
    ws = MagicMock()
    ws.id = workspace_id or uuid4()
    return ws


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


class TestDetectProvider:
    @pytest.mark.unit
    def test_github_ssh(self) -> None:
        assert _detect_provider("git@github.com:owner/repo.git") == "github"

    @pytest.mark.unit
    def test_github_https(self) -> None:
        assert _detect_provider("https://github.com/owner/repo") == "github"

    @pytest.mark.unit
    def test_gitlab(self) -> None:
        assert _detect_provider("git@gitlab.com:owner/repo.git") == "gitlab"

    @pytest.mark.unit
    def test_bitbucket(self) -> None:
        assert _detect_provider("git@bitbucket.org:owner/repo.git") == "bitbucket"

    @pytest.mark.unit
    def test_unknown(self) -> None:
        assert _detect_provider("git@selfhosted.example.com:owner/repo.git") == "local"


class TestNormalizeRemoteUrl:
    @pytest.mark.unit
    def test_ssh_to_https(self) -> None:
        assert _normalize_remote_url("git@github.com:owner/repo.git") == "https://github.com/owner/repo"

    @pytest.mark.unit
    def test_https_strips_dot_git(self) -> None:
        assert _normalize_remote_url("https://github.com/owner/repo.git") == "https://github.com/owner/repo"

    @pytest.mark.unit
    def test_https_no_dot_git(self) -> None:
        assert _normalize_remote_url("https://github.com/owner/repo") == "https://github.com/owner/repo"

    @pytest.mark.unit
    def test_gitlab_ssh(self) -> None:
        assert _normalize_remote_url("git@gitlab.com:owner/repo.git") == "https://gitlab.com/owner/repo"


# ---------------------------------------------------------------------------
# Workflow tests
# ---------------------------------------------------------------------------


class TestProjectSetupWorkflow:
    """Tests for ProjectSetupWorkflow.create_local_project."""

    @pytest.mark.unit
    async def test_happy_path_github_remote(self, tmp_path) -> None:
        """Valid local_path with GitHub remote creates project + workspace + transitions."""
        # Set up a fake git repo
        repo = tmp_path / "my-repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        user_id = uuid4()
        project = _mock_project(name="my-repo")
        workspace = _mock_workspace()

        db = AsyncMock()
        workflow = ProjectSetupWorkflow(db=db)
        workflow.project_service = MagicMock()
        workflow.project_service.get_by_name = AsyncMock(return_value=None)
        workflow.project_service.create = AsyncMock(return_value=project)
        workflow.workspace_service = MagicMock()
        workflow.workspace_service.create = AsyncMock(return_value=workspace)

        # Mock git commands: remote returns GitHub URL, symbolic-ref returns "main"
        remote_proc = _make_process("https://github.com/owner/my-repo.git", returncode=0)
        branch_proc = _make_process("main", returncode=0)

        with patch(
            "molecules.workflows.project_setup.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=[remote_proc, branch_proc]),
        ):
            result = await workflow.create_local_project(
                user_id=user_id,
                name="my-repo",
                local_path=str(repo),
            )

        # Verify result
        assert result.project_id == project.id
        assert result.workspace_id == workspace.id
        assert result.project_name == "my-repo"

        # Verify project creation
        create_call = workflow.project_service.create.call_args
        project_data = create_call[0][1]
        assert project_data.github_repo == "https://github.com/owner/my-repo"
        assert project_data.owner_id == user_id
        assert project_data.local_path == str(repo)

        # Verify workspace creation
        ws_call = workflow.workspace_service.create.call_args
        ws_data = ws_call[0][1]
        assert ws_data.provider == "github"
        assert ws_data.repo_url == "https://github.com/owner/my-repo"
        assert ws_data.default_branch == "main"
        assert ws_data.local_path == str(repo)

        # Verify transition
        project.transition_to.assert_called_once_with("active")
        db.flush.assert_awaited_once()

    @pytest.mark.unit
    async def test_no_remote_uses_synthetic_url(self, tmp_path) -> None:
        """Local path with no remote uses synthetic github_repo URL, provider=local."""
        repo = tmp_path / "local-only"
        repo.mkdir()
        (repo / ".git").mkdir()

        user_id = uuid4()
        project = _mock_project(name="local-only")
        workspace = _mock_workspace()

        db = AsyncMock()
        workflow = ProjectSetupWorkflow(db=db)
        workflow.project_service = MagicMock()
        workflow.project_service.get_by_name = AsyncMock(return_value=None)
        workflow.project_service.create = AsyncMock(return_value=project)
        workflow.workspace_service = MagicMock()
        workflow.workspace_service.create = AsyncMock(return_value=workspace)

        # remote fails (no origin), branch succeeds
        remote_proc = _make_process("", returncode=128)
        branch_proc = _make_process("develop", returncode=0)

        with patch(
            "molecules.workflows.project_setup.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=[remote_proc, branch_proc]),
        ):
            result = await workflow.create_local_project(
                user_id=user_id,
                name="local-only",
                local_path=str(repo),
            )

        assert result.project_name == "local-only"

        # Verify synthetic github_repo
        project_data = workflow.project_service.create.call_args[0][1]
        assert project_data.github_repo == "https://github.com/local/local-only"

        # Verify workspace uses local provider
        ws_data = workflow.workspace_service.create.call_args[0][1]
        assert ws_data.provider == "local"
        assert ws_data.repo_url == "https://github.com/local/local-only"
        assert ws_data.default_branch == "develop"

    @pytest.mark.unit
    async def test_gitlab_remote_uses_synthetic_github_repo(self, tmp_path) -> None:
        """GitLab remote uses synthetic github_repo (to pass schema validator) but real repo_url."""
        repo = tmp_path / "gl-project"
        repo.mkdir()
        (repo / ".git").mkdir()

        user_id = uuid4()
        project = _mock_project(name="gl-project")
        workspace = _mock_workspace()

        db = AsyncMock()
        workflow = ProjectSetupWorkflow(db=db)
        workflow.project_service = MagicMock()
        workflow.project_service.get_by_name = AsyncMock(return_value=None)
        workflow.project_service.create = AsyncMock(return_value=project)
        workflow.workspace_service = MagicMock()
        workflow.workspace_service.create = AsyncMock(return_value=workspace)

        remote_proc = _make_process("git@gitlab.com:owner/gl-project.git", returncode=0)
        branch_proc = _make_process("main", returncode=0)

        with patch(
            "molecules.workflows.project_setup.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=[remote_proc, branch_proc]),
        ):
            result = await workflow.create_local_project(
                user_id=user_id,
                name="gl-project",
                local_path=str(repo),
            )

        assert result.project_name == "gl-project"

        # github_repo must pass the "github.com" validator — synthetic URL
        project_data = workflow.project_service.create.call_args[0][1]
        assert "github.com" in project_data.github_repo
        assert project_data.github_repo == "https://github.com/local/gl-project"

        # workspace repo_url should be the real GitLab URL
        ws_data = workflow.workspace_service.create.call_args[0][1]
        assert ws_data.repo_url == "https://gitlab.com/owner/gl-project"
        assert ws_data.provider == "gitlab"

    @pytest.mark.unit
    async def test_nonexistent_path_raises(self) -> None:
        """Path that does not exist raises ProjectSetupError."""
        db = AsyncMock()
        workflow = ProjectSetupWorkflow(db=db)

        with pytest.raises(ProjectSetupError, match="Directory does not exist"):
            await workflow.create_local_project(
                user_id=uuid4(),
                name="nope",
                local_path="/nonexistent/path/that/does/not/exist",
            )

    @pytest.mark.unit
    async def test_not_a_git_repo_raises(self, tmp_path) -> None:
        """Path that exists but has no .git directory raises ProjectSetupError."""
        not_git = tmp_path / "not-a-repo"
        not_git.mkdir()

        db = AsyncMock()
        workflow = ProjectSetupWorkflow(db=db)

        with pytest.raises(ProjectSetupError, match="Not a git repository"):
            await workflow.create_local_project(
                user_id=uuid4(),
                name="not-a-repo",
                local_path=str(not_git),
            )

    @pytest.mark.unit
    async def test_path_is_file_raises(self, tmp_path) -> None:
        """Path that is a file (not a directory) raises ProjectSetupError."""
        file_path = tmp_path / "some-file.txt"
        file_path.write_text("hello")

        db = AsyncMock()
        workflow = ProjectSetupWorkflow(db=db)

        with pytest.raises(ProjectSetupError, match="Path is not a directory"):
            await workflow.create_local_project(
                user_id=uuid4(),
                name="oops",
                local_path=str(file_path),
            )

    @pytest.mark.unit
    async def test_duplicate_name_raises(self, tmp_path) -> None:
        """Duplicate project name raises ProjectSetupError."""
        repo = tmp_path / "dup-repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        db = AsyncMock()
        workflow = ProjectSetupWorkflow(db=db)
        workflow.project_service = MagicMock()
        workflow.project_service.get_by_name = AsyncMock(
            return_value=MagicMock()  # existing project found
        )

        remote_proc = _make_process("https://github.com/owner/dup-repo", returncode=0)
        branch_proc = _make_process("main", returncode=0)

        with (
            patch(
                "molecules.workflows.project_setup.asyncio.create_subprocess_exec",
                AsyncMock(side_effect=[remote_proc, branch_proc]),
            ),
            pytest.raises(ProjectSetupError, match="already exists"),
        ):
            await workflow.create_local_project(
                user_id=uuid4(),
                name="dup-repo",
                local_path=str(repo),
            )

    @pytest.mark.unit
    async def test_branch_fallback_to_main(self, tmp_path) -> None:
        """When symbolic-ref fails, default branch falls back to 'main'."""
        repo = tmp_path / "detached-repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        user_id = uuid4()
        project = _mock_project(name="detached-repo")
        workspace = _mock_workspace()

        db = AsyncMock()
        workflow = ProjectSetupWorkflow(db=db)
        workflow.project_service = MagicMock()
        workflow.project_service.get_by_name = AsyncMock(return_value=None)
        workflow.project_service.create = AsyncMock(return_value=project)
        workflow.workspace_service = MagicMock()
        workflow.workspace_service.create = AsyncMock(return_value=workspace)

        # remote succeeds, but branch fails (detached HEAD)
        remote_proc = _make_process("https://github.com/owner/detached-repo", returncode=0)
        branch_proc = _make_process("", returncode=128)

        with patch(
            "molecules.workflows.project_setup.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=[remote_proc, branch_proc]),
        ):
            await workflow.create_local_project(
                user_id=user_id,
                name="detached-repo",
                local_path=str(repo),
            )

        ws_data = workflow.workspace_service.create.call_args[0][1]
        assert ws_data.default_branch == "main"

    @pytest.mark.unit
    async def test_custom_description(self, tmp_path) -> None:
        """Custom description is passed through to the project."""
        repo = tmp_path / "desc-repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        project = _mock_project(name="desc-repo")
        workspace = _mock_workspace()

        db = AsyncMock()
        workflow = ProjectSetupWorkflow(db=db)
        workflow.project_service = MagicMock()
        workflow.project_service.get_by_name = AsyncMock(return_value=None)
        workflow.project_service.create = AsyncMock(return_value=project)
        workflow.workspace_service = MagicMock()
        workflow.workspace_service.create = AsyncMock(return_value=workspace)

        remote_proc = _make_process("https://github.com/owner/desc-repo", returncode=0)
        branch_proc = _make_process("main", returncode=0)

        with patch(
            "molecules.workflows.project_setup.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=[remote_proc, branch_proc]),
        ):
            await workflow.create_local_project(
                user_id=uuid4(),
                name="desc-repo",
                local_path=str(repo),
                description="My custom description",
            )

        project_data = workflow.project_service.create.call_args[0][1]
        assert project_data.description == "My custom description"
