"""Tests for StackAPI._get_reader_for_branch adapter resolution logic.

Verifies that the correct git adapter (LocalGitAdapter vs GitHubAdapter)
is selected based on workspace configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from molecules.providers.local_git_adapter import LocalGitAdapter


class TestGetReaderForBranch:
    """Test StackAPI._get_reader_for_branch resolution."""

    def _make_branch(self, workspace_id: str | None = None) -> MagicMock:
        branch = MagicMock()
        branch.id = uuid4()
        branch.workspace_id = workspace_id or uuid4()
        branch.stack_id = uuid4()
        return branch

    def _make_workspace(self, local_path: str | None = None, repo_url: str = "https://github.com/o/r") -> MagicMock:
        ws = MagicMock()
        ws.id = uuid4()
        ws.local_path = local_path
        ws.repo_url = repo_url
        return ws

    def _make_stack_api(
        self, github: MagicMock | None = None, workspace: MagicMock | None = None, branch: MagicMock | None = None
    ) -> MagicMock:
        """Create a StackAPI-like object with mocked dependencies."""
        from molecules.apis.stack_api import StackAPI

        db = AsyncMock()
        api = StackAPI.__new__(StackAPI)
        api.db = db
        api.github = github
        api.entity = MagicMock()
        api.entity.get_branch = AsyncMock(return_value=branch or self._make_branch())
        api.entity.workspace_service = MagicMock()
        api.entity.workspace_service.get = AsyncMock(return_value=workspace)
        api._comment_svc = MagicMock()
        return api

    @pytest.mark.unit
    async def test_local_path_exists_returns_local_adapter(self, tmp_path: Path) -> None:
        """Workspace with valid local_path returns LocalGitAdapter."""
        # Create a .git directory to make it look like a real repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        workspace = self._make_workspace(local_path=str(tmp_path))
        branch = self._make_branch(workspace_id=workspace.id)
        api = self._make_stack_api(workspace=workspace, branch=branch)

        reader = await api._get_reader_for_branch(branch.id)

        assert isinstance(reader, LocalGitAdapter)
        assert reader.repo_path == str(tmp_path)

    @pytest.mark.unit
    async def test_local_path_not_git_repo_falls_back_to_github(self, tmp_path: Path) -> None:
        """Workspace with local_path but no .git dir falls back to GitHub."""
        github = MagicMock()
        workspace = self._make_workspace(local_path=str(tmp_path))
        branch = self._make_branch(workspace_id=workspace.id)
        api = self._make_stack_api(github=github, workspace=workspace, branch=branch)

        reader = await api._get_reader_for_branch(branch.id)

        assert reader is github

    @pytest.mark.unit
    async def test_no_local_path_uses_github(self) -> None:
        """Workspace without local_path uses GitHub adapter."""
        github = MagicMock()
        workspace = self._make_workspace(local_path=None)
        branch = self._make_branch(workspace_id=workspace.id)
        api = self._make_stack_api(github=github, workspace=workspace, branch=branch)

        reader = await api._get_reader_for_branch(branch.id)

        assert reader is github

    @pytest.mark.unit
    async def test_no_local_path_no_github_raises(self) -> None:
        """Workspace without local_path and no GitHub adapter raises RuntimeError."""
        workspace = self._make_workspace(local_path=None)
        branch = self._make_branch(workspace_id=workspace.id)
        api = self._make_stack_api(github=None, workspace=workspace, branch=branch)

        with pytest.raises(RuntimeError, match="No git reader available"):
            await api._get_reader_for_branch(branch.id)

    @pytest.mark.unit
    async def test_local_path_nonexistent_dir_falls_back(self) -> None:
        """Workspace with local_path that doesn't exist falls back to GitHub."""
        github = MagicMock()
        workspace = self._make_workspace(local_path="/nonexistent/path")
        branch = self._make_branch(workspace_id=workspace.id)
        api = self._make_stack_api(github=github, workspace=workspace, branch=branch)

        reader = await api._get_reader_for_branch(branch.id)

        assert reader is github

    @pytest.mark.unit
    async def test_missing_workspace_raises(self) -> None:
        """Missing workspace raises BranchNotFoundError."""
        from molecules.exceptions import BranchNotFoundError

        branch = self._make_branch()
        api = self._make_stack_api(workspace=None, branch=branch)

        with pytest.raises(BranchNotFoundError):
            await api._get_reader_for_branch(branch.id)
