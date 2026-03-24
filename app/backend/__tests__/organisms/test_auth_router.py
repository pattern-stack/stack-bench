from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.github_connections.schemas.output import GitHubConnectionResponse
from molecules.apis.github_oauth_api import _pending_oauth
from organisms.api.routers.auth import router


@pytest.fixture(autouse=True)
def clear_pending_oauth() -> None:
    """Clear pending OAuth state between tests."""
    _pending_oauth.clear()


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the auth router."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a TestClient for the app."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture(autouse=True)
def patch_dependencies(mock_db: AsyncMock) -> None:  # type: ignore[misc]
    """Patch database dependency for all tests."""
    from organisms.api.routers import auth

    async def override_get_db():  # type: ignore[no-untyped-def]
        yield mock_db

    auth._get_db_override = override_get_db  # type: ignore[attr-defined]


@pytest.mark.integration
def test_github_auth_redirect(client: TestClient) -> None:
    """GET /auth/github?code_verifier=... returns 307 redirect to github.com."""
    with patch("organisms.api.routers.auth.GitHubOAuthAPI") as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.build_authorize_url.return_value = (
            "https://github.com/login/oauth/authorize?client_id=test&code_challenge=abc&code_challenge_method=S256",
            "test-state",
        )

        response = client.get(
            "/api/v1/auth/github",
            params={"code_verifier": "test-verifier-at-least-43-chars-long-for-pkce"},
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert "github.com" in response.headers["location"]
    assert "authorize" in response.headers["location"]


@pytest.mark.integration
def test_github_auth_redirect_contains_pkce(client: TestClient) -> None:
    """Redirect URL contains PKCE params."""
    with patch("organisms.api.routers.auth.GitHubOAuthAPI") as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.build_authorize_url.return_value = (
            "https://github.com/login/oauth/authorize?client_id=test&code_challenge=abc123&code_challenge_method=S256&redirect_uri=http%3A%2F%2Flocalhost",
            "test-state",
        )

        response = client.get(
            "/api/v1/auth/github",
            params={"code_verifier": "test-verifier-at-least-43-chars-long-for-pkce"},
            follow_redirects=False,
        )

    location = response.headers["location"]
    assert "code_challenge=" in location
    assert "code_challenge_method=S256" in location


@pytest.mark.integration
def test_github_callback_success(client: TestClient) -> None:
    """GET /auth/github/callback with valid code redirects to frontend."""
    mock_response = GitHubConnectionResponse(
        id=uuid4(),
        github_user_id=12345,
        github_login="testuser",
        token_expires_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
        connected=True,
        created_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
    )

    with patch("organisms.api.routers.auth.GitHubOAuthAPI") as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.handle_callback = AsyncMock(return_value=mock_response)
        mock_api.settings = MagicMock()
        mock_api.settings.FRONTEND_URL = "http://localhost:3500"

        with patch("organisms.api.routers.auth.get_settings") as mock_get_settings:
            mock_get_settings.return_value.FRONTEND_URL = "http://localhost:3500"

            response = client.get(
                "/api/v1/auth/github/callback",
                params={"code": "test-code", "state": "test-state"},
                follow_redirects=False,
            )

    assert response.status_code == 307
    assert "localhost:3500" in response.headers["location"]
    assert "github=connected" in response.headers["location"]


@pytest.mark.integration
def test_github_callback_invalid_state(client: TestClient) -> None:
    """GET /auth/github/callback with invalid state redirects with error."""
    with patch("organisms.api.routers.auth.GitHubOAuthAPI") as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.handle_callback = AsyncMock(side_effect=ValueError("Invalid state"))

        with patch("organisms.api.routers.auth.get_settings") as mock_get_settings:
            mock_get_settings.return_value.FRONTEND_URL = "http://localhost:3500"

            response = client.get(
                "/api/v1/auth/github/callback",
                params={"code": "test-code", "state": "invalid-state"},
                follow_redirects=False,
            )

    assert response.status_code == 307
    assert "github=error" in response.headers["location"]


@pytest.mark.integration
def test_github_status_disconnected(client: TestClient) -> None:
    """GET /auth/github/status returns connected=false when no connection."""
    with patch("organisms.api.routers.auth.GitHubOAuthAPI") as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.get_connection_status = AsyncMock(return_value=None)

        response = client.get("/api/v1/auth/github/status")

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["github_login"] is None


@pytest.mark.integration
def test_github_status_connected(client: TestClient) -> None:
    """GET /auth/github/status returns connection info when connected."""
    mock_response = GitHubConnectionResponse(
        id=uuid4(),
        github_user_id=12345,
        github_login="testuser",
        token_expires_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
        connected=True,
        created_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
    )

    with patch("organisms.api.routers.auth.GitHubOAuthAPI") as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.get_connection_status = AsyncMock(return_value=mock_response)

        response = client.get("/api/v1/auth/github/status")

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["github_login"] == "testuser"
