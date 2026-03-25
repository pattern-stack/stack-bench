"""API-level tests for GitHub OAuth router endpoints (Phase 2)."""

from uuid import uuid4

import pytest


def _email() -> str:
    return f"test-{uuid4().hex[:8]}@stackbench.dev"


@pytest.mark.integration
class TestGitHubAuthorize:
    """GET /api/v1/auth/github tests."""

    async def test_returns_authorize_url(self, client):
        response = client.get("/api/v1/auth/github")
        assert response.status_code == 200
        data = response.json()
        assert "authorize_url" in data
        assert "state" in data
        assert "github.com/login/oauth/authorize" in data["authorize_url"]
        assert "client_id=" in data["authorize_url"]
        assert "scope=" in data["authorize_url"]


@pytest.mark.integration
class TestGitHubConnectionStatus:
    """GET /api/v1/auth/github/status tests."""

    async def test_not_connected(self, client):
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Status",
                "last_name": "Test",
                "email": _email(),
                "password": "Str0ng!Pass#1",
            },
        )
        assert reg.status_code == 201, f"Register failed: {reg.json()}"
        access_token = reg.json()["access_token"]

        response = client.get(
            "/api/v1/auth/github/status",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False

    async def test_requires_auth(self, client):
        response = client.get("/api/v1/auth/github/status")
        assert response.status_code == 401


@pytest.mark.integration
class TestGitHubDisconnect:
    """DELETE /api/v1/auth/github tests."""

    async def test_disconnect_no_connection(self, client):
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Disconnect",
                "last_name": "Test",
                "email": _email(),
                "password": "Str0ng!Pass#1",
            },
        )
        assert reg.status_code == 201, f"Register failed: {reg.json()}"
        access_token = reg.json()["access_token"]

        response = client.delete(
            "/api/v1/auth/github",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 204

    async def test_requires_auth(self, client):
        response = client.delete("/api/v1/auth/github")
        assert response.status_code == 401
