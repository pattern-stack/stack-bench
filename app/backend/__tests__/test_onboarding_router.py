"""Tests for onboarding router endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from molecules.workflows.onboarding import (
    GitHubOrg,
    GitHubRepo,
    OnboardingError,
    OnboardingStatus,
)


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    return user


@pytest.fixture
def unit_client(mock_user):
    """Standalone test client with mocked auth and DB — no Postgres needed."""
    from organisms.api.app import create_app
    from organisms.api.dependencies import get_current_user, get_db

    app = create_app()

    async def override_get_db():  # type: ignore[no-untyped-def]
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as c:
        yield c, mock_user

    app.dependency_overrides.clear()


def _auth_headers(token: str = "test-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.unit
class TestOnboardingStatusEndpoint:
    def test_unauthenticated(self):
        """A request without any auth override should get 401.

        We use a fresh app with no dependency overrides for this test.
        """
        from organisms.api.app import create_app
        from organisms.api.dependencies import get_db

        app = create_app()

        async def override_get_db():  # type: ignore[no-untyped-def]
            yield AsyncMock()

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as c:
            response = c.get("/api/v1/onboarding/status")
        assert response.status_code == 401

    def test_needs_onboarding(self, unit_client):
        client, user = unit_client
        mock_status = OnboardingStatus(needs_onboarding=True, has_github=False, has_project=False)

        with patch("organisms.api.routers.onboarding.OnboardingWorkflow") as MockWorkflow:
            instance = MockWorkflow.return_value
            instance.get_status = AsyncMock(return_value=mock_status)

            response = client.get("/api/v1/onboarding/status", headers=_auth_headers())

        assert response.status_code == 200
        data = response.json()
        assert data["needs_onboarding"] is True
        assert data["has_github"] is False
        assert data["has_project"] is False


@pytest.mark.unit
class TestGitHubOrgsEndpoint:
    def test_success(self, unit_client):
        client, user = unit_client
        mock_orgs = [
            GitHubOrg(login="dug", avatar_url="https://avatar.com/dug", description="Personal account"),
            GitHubOrg(login="my-org", avatar_url="https://avatar.com/org", description="My Org"),
        ]

        with patch("organisms.api.routers.onboarding.OnboardingWorkflow") as MockWorkflow:
            instance = MockWorkflow.return_value
            instance.list_github_orgs = AsyncMock(return_value=mock_orgs)

            response = client.get("/api/v1/onboarding/github/orgs", headers=_auth_headers())

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["login"] == "dug"
        assert data[1]["login"] == "my-org"

    def test_no_github_connection(self, unit_client):
        client, user = unit_client

        with patch("organisms.api.routers.onboarding.OnboardingWorkflow") as MockWorkflow:
            instance = MockWorkflow.return_value
            instance.list_github_orgs = AsyncMock(side_effect=OnboardingError("GitHub not connected"))

            response = client.get("/api/v1/onboarding/github/orgs", headers=_auth_headers())

        assert response.status_code == 400
        assert "GitHub not connected" in response.json()["detail"]


@pytest.mark.unit
class TestGitHubReposEndpoint:
    def test_success(self, unit_client):
        client, user = unit_client
        mock_repos = [
            GitHubRepo(
                full_name="dug/backend",
                name="backend",
                private=False,
                default_branch="main",
                description="Backend repo",
            ),
        ]

        with patch("organisms.api.routers.onboarding.OnboardingWorkflow") as MockWorkflow:
            instance = MockWorkflow.return_value
            instance.list_github_repos = AsyncMock(return_value=mock_repos)

            response = client.get(
                "/api/v1/onboarding/github/repos",
                headers=_auth_headers(),
                params={"org": "dug"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["full_name"] == "dug/backend"


@pytest.mark.unit
class TestCompleteEndpoint:
    def test_success(self, unit_client):
        client, user = unit_client

        with patch("organisms.api.routers.onboarding.OnboardingWorkflow") as MockWorkflow:
            instance = MockWorkflow.return_value
            instance.mark_complete = AsyncMock(return_value=None)

            response = client.post(
                "/api/v1/onboarding/complete",
                headers=_auth_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is True
