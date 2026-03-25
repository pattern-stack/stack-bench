"""Integration tests for auth endpoints wired via pattern-stack.

These tests require a running Postgres database. They are automatically
skipped when the database is not reachable (e.g., in CI without a DB service).
"""

import time

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.settings import get_settings


def _db_is_reachable() -> bool:
    """Check if the database is reachable (sync check at import time)."""
    try:
        from sqlalchemy import create_engine, text

        settings = get_settings()
        # Convert async URL to sync for a quick connectivity check
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
        engine = create_engine(sync_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


_DB_AVAILABLE = _db_is_reachable()
skip_no_db = pytest.mark.skipif(not _DB_AVAILABLE, reason="Database not reachable")


@pytest.fixture
async def client():
    """Async HTTP client with lifespan initialized."""
    from organisms.api.app import create_app

    app = create_app()

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


@skip_no_db
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


@skip_no_db
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


@skip_no_db
@pytest.mark.integration
async def test_login_wrong_password(client: AsyncClient) -> None:
    result = await _register(client)
    email = result["email"]

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPass1!"},
    )
    assert resp.status_code == 401


@skip_no_db
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


@skip_no_db
@pytest.mark.integration
async def test_me_without_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403, 422)


@skip_no_db
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


@skip_no_db
@pytest.mark.integration
async def test_register_duplicate_email(client: AsyncClient) -> None:
    email = _unique_email()
    await _register(client, email=email)

    result2 = await _register(client, email=email)
    resp = result2["response"]
    assert resp.status_code in (400, 409, 422), resp.text
