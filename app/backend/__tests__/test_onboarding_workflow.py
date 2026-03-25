"""Unit tests for OnboardingWorkflow molecule."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from molecules.workflows.onboarding import (
    OnboardingError,
    OnboardingWorkflow,
)


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_github_oauth():
    return MagicMock()


@pytest.fixture
def mock_project_service():
    return MagicMock()


@pytest.fixture
def mock_workspace_service():
    return MagicMock()


@pytest.fixture
def workflow(mock_db, mock_github_oauth, mock_project_service, mock_workspace_service):
    return OnboardingWorkflow(
        db=mock_db,
        github_oauth=mock_github_oauth,
        project_service=mock_project_service,
        workspace_service=mock_workspace_service,
    )


@pytest.mark.unit
class TestGetStatus:
    async def test_no_github_no_project(self, workflow, mock_github_oauth, mock_project_service):
        user_id = uuid4()
        mock_github_oauth.get_connection_status = AsyncMock(return_value={"connected": False})
        mock_project_service.get_by_owner = AsyncMock(return_value=[])

        status = await workflow.get_status(user_id)

        assert status.needs_onboarding is True
        assert status.has_github is False
        assert status.has_project is False

    async def test_has_github_no_project(self, workflow, mock_github_oauth, mock_project_service):
        user_id = uuid4()
        mock_github_oauth.get_connection_status = AsyncMock(return_value={"connected": True})
        mock_project_service.get_by_owner = AsyncMock(return_value=[])

        status = await workflow.get_status(user_id)

        assert status.needs_onboarding is True
        assert status.has_github is True
        assert status.has_project is False

    async def test_has_project(self, workflow, mock_github_oauth, mock_project_service):
        user_id = uuid4()
        mock_github_oauth.get_connection_status = AsyncMock(return_value={"connected": True})
        mock_project_service.get_by_owner = AsyncMock(return_value=[MagicMock()])

        status = await workflow.get_status(user_id)

        assert status.needs_onboarding is False
        assert status.has_github is True
        assert status.has_project is True


@pytest.mark.unit
class TestListGitHubOrgs:
    async def test_returns_personal_plus_orgs(self, workflow, mock_github_oauth):
        user_id = uuid4()
        mock_github_oauth.get_user_github_token = AsyncMock(return_value="gh_token_123")
        mock_github_oauth.get_github_user = AsyncMock(
            return_value={"login": "dug", "avatar_url": "https://avatar.com/dug"}
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"login": "my-org", "avatar_url": "https://avatar.com/org", "description": "My Org"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("molecules.workflows.onboarding.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            orgs = await workflow.list_github_orgs(user_id)

        assert len(orgs) == 2
        assert orgs[0].login == "dug"
        assert orgs[0].description == "Personal account"
        assert orgs[1].login == "my-org"

    async def test_no_github_token_raises(self, workflow, mock_github_oauth):
        user_id = uuid4()
        mock_github_oauth.get_user_github_token = AsyncMock(return_value=None)

        with pytest.raises(OnboardingError, match="GitHub not connected"):
            await workflow.list_github_orgs(user_id)


@pytest.mark.unit
class TestListGitHubRepos:
    async def test_returns_repos_for_org(self, workflow, mock_github_oauth):
        user_id = uuid4()
        mock_github_oauth.get_user_github_token = AsyncMock(return_value="gh_token_123")
        mock_github_oauth.get_github_user = AsyncMock(return_value={"login": "dug"})

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "full_name": "my-org/backend",
                "name": "backend",
                "private": False,
                "default_branch": "main",
                "description": "Backend repo",
                "html_url": "https://github.com/my-org/backend",
            },
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("molecules.workflows.onboarding.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            repos = await workflow.list_github_repos(user_id, org="my-org")

        assert len(repos) == 1
        assert repos[0].full_name == "my-org/backend"
        assert repos[0].private is False

    async def test_returns_personal_repos(self, workflow, mock_github_oauth):
        user_id = uuid4()
        mock_github_oauth.get_user_github_token = AsyncMock(return_value="gh_token_123")
        mock_github_oauth.get_github_user = AsyncMock(return_value={"login": "dug"})

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "full_name": "dug/my-repo",
                "name": "my-repo",
                "private": True,
                "default_branch": "main",
                "description": None,
                "html_url": "https://github.com/dug/my-repo",
            },
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("molecules.workflows.onboarding.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            repos = await workflow.list_github_repos(user_id, org="dug")

        assert len(repos) == 1
        assert repos[0].full_name == "dug/my-repo"
        assert repos[0].private is True

    async def test_no_github_token_raises(self, workflow, mock_github_oauth):
        user_id = uuid4()
        mock_github_oauth.get_user_github_token = AsyncMock(return_value=None)

        with pytest.raises(OnboardingError, match="GitHub not connected"):
            await workflow.list_github_repos(user_id)


@pytest.mark.unit
class TestComplete:
    async def test_creates_project_and_workspace(self, workflow, mock_project_service, mock_workspace_service, mock_db):
        user_id = uuid4()
        project_id = uuid4()
        workspace_id = uuid4()

        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.name = "dug/backend"
        mock_project.transition_to = MagicMock()

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id

        mock_project_service.get_by_name = AsyncMock(return_value=None)
        mock_project_service.create = AsyncMock(return_value=mock_project)
        mock_workspace_service.create = AsyncMock(return_value=mock_workspace)
        mock_db.flush = AsyncMock()

        result = await workflow.complete(user_id, "dug/backend")

        assert result.project_id == project_id
        assert result.workspace_id == workspace_id
        assert result.project_name == "dug/backend"
        mock_project.transition_to.assert_called_once_with("active")
        mock_project_service.create.assert_called_once()
        mock_workspace_service.create.assert_called_once()

    async def test_duplicate_project_name_raises(self, workflow, mock_project_service):
        user_id = uuid4()
        mock_project_service.get_by_name = AsyncMock(return_value=MagicMock())

        with pytest.raises(OnboardingError, match="already exists"):
            await workflow.complete(user_id, "dug/backend")
