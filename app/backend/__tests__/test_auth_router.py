"""Tests for auth router (Phase 1): login, register, refresh, me."""

from uuid import uuid4

import pytest


def _email() -> str:
    """Generate a unique email for test isolation."""
    return f"test-{uuid4().hex[:8]}@stackbench.dev"


@pytest.mark.integration
class TestAuthRegister:
    """POST /api/v1/auth/register tests."""

    async def test_register_new_user(self, client):
        email = _email()
        response = client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": email,
                "password": "Str0ng!Pass#1",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == email
        assert data["user"]["first_name"] == "Test"
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client):
        email = _email()
        # First registration
        client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": email,
                "password": "Str0ng!Pass#1",
            },
        )
        # Duplicate
        response = client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Test",
                "last_name": "User2",
                "email": email,
                "password": "Str0ng!Pass#2",
            },
        )
        assert response.status_code == 409

    async def test_register_weak_password(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": _email(),
                "password": "weak",
            },
        )
        # FastAPI validates min_length=8 from RegisterRequest schema
        assert response.status_code == 422


@pytest.mark.integration
class TestAuthLogin:
    """POST /api/v1/auth/login tests."""

    async def test_login_valid_credentials(self, client):
        email = _email()
        client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Login",
                "last_name": "Test",
                "email": email,
                "password": "Str0ng!Pass#1",
            },
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Str0ng!Pass#1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client):
        email = _email()
        client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Wrong",
                "last_name": "Pass",
                "email": email,
                "password": "Str0ng!Pass#1",
            },
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword#1"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_email(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": _email(), "password": "Str0ng!Pass#1"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestAuthRefresh:
    """POST /api/v1/auth/refresh tests."""

    async def test_refresh_with_valid_token(self, client):
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Refresh",
                "last_name": "Test",
                "email": _email(),
                "password": "Str0ng!Pass#1",
            },
        )
        refresh_token = reg.json()["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_refresh_with_invalid_token(self, client):
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token-here"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestAuthMe:
    """GET /api/v1/auth/me tests."""

    async def test_me_with_valid_token(self, client):
        email = _email()
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Me",
                "last_name": "Test",
                "email": email,
                "password": "Str0ng!Pass#1",
            },
        )
        access_token = reg.json()["access_token"]

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert data["first_name"] == "Me"

    async def test_me_without_token(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_me_with_invalid_token(self, client):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
