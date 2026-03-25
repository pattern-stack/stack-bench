"""Integration tests for auth endpoints wired via pattern-stack."""

import time

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.settings import get_settings
from organisms.api.app import create_app


@pytest.fixture
async def client():
    """Async HTTP client with lifespan initialized."""
    app = create_app()

    # Manually set up DB on app state (mirroring lifespan)
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.engine = engine
    app.state.session_factory = session_factory

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    await engine.dispose()


# Unique email per test run to avoid collisions
_base = int(time.time() * 1000)
_counter = 0


def _unique_email() -> str:
    global _counter
    _counter += 1
    return f"testuser{_base}_{_counter}@example.com"


async def _register(client: AsyncClient, email: str | None = None) -> dict:
    """Helper: register a new user, return response JSON."""
    email = email or _unique_email()
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": "Str0ng!Pass",
        },
    )
    return {"response": resp, "email": email}


@pytest.mark.integration
async def test_register_success(client: AsyncClient) -> None:
    result = await _register(client)
    resp = result["response"]
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == result["email"]
    assert data["user"]["first_name"] == "Test"


@pytest.mark.integration
async def test_login_success(client: AsyncClient) -> None:
    result = await _register(client)
    email = result["email"]

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Str0ng!Pass"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == email


@pytest.mark.integration
async def test_login_wrong_password(client: AsyncClient) -> None:
    result = await _register(client)
    email = result["email"]

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPass1!"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_me_with_valid_token(client: AsyncClient) -> None:
    result = await _register(client)
    token = result["response"].json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["email"] == result["email"]


@pytest.mark.integration
async def test_me_without_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403, 422)


@pytest.mark.integration
async def test_refresh_token(client: AsyncClient) -> None:
    result = await _register(client)
    refresh_token = result["response"].json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data


@pytest.mark.integration
async def test_register_duplicate_email(client: AsyncClient) -> None:
    email = _unique_email()
    await _register(client, email=email)

    result2 = await _register(client, email=email)
    resp = result2["response"]
    assert resp.status_code in (400, 409, 422), resp.text
