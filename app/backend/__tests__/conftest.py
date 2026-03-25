"""Test fixtures for stack-bench backend tests.

Provides database, app, and client fixtures. Uses the dev Postgres
instance. Tests should use unique identifiers to avoid conflicts.
"""

import contextlib
import socket
from collections.abc import AsyncGenerator, Generator
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pattern_stack.atoms.config import settings as ps_settings
from pattern_stack.atoms.config.auth import get_cached_auth_config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


def _postgres_reachable(url: str) -> bool:
    """Check if Postgres is reachable by probing the port."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url.replace("+asyncpg", ""))
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=1):
            return True
    except (OSError, TimeoutError):
        return False


# Import all models so they're registered
import features  # noqa: E402, F401

# Ensure JWT secret is configured for tests
ps_settings.JWT_SECRET_KEY = "test-secret-for-conftest-key-must-be-32-chars-long!"

# Clear the cached auth config so it picks up the new key
get_cached_auth_config.cache_clear()

# Load pattern-stack's pytest plugin for BasePattern test mode
pytest_plugins = ["pattern_stack.testing.pytest_plugin"]


def _postgres_reachable(url: str) -> bool:
    """Check if Postgres is reachable by probing the port."""
    try:
        parsed = urlparse(url.replace("+asyncpg", ""))
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=1):
            return True
    except (OSError, TimeoutError):
        return False


@pytest.fixture(scope="session")
def database_url() -> str:
    """Use the dev Postgres instance for integration tests.

    Skips the test if Postgres is not reachable.
    """
    from config.settings import get_settings

    url = get_settings().DATABASE_URL
    if not _postgres_reachable(url):
        pytest.skip("Postgres not reachable — start with `pts services up`")
    return url


@pytest_asyncio.fixture(scope="function")
async def async_engine(database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Function-scoped engine."""
    engine = create_async_engine(database_url, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Function-scoped database session."""
    session_factory = async_sessionmaker(
        async_engine,
        expire_on_commit=False,
    )
    session = session_factory()
    yield session
    # Don't try to rollback - the session may have been committed by routes
    # Just close it cleanly
    with contextlib.suppress(Exception):
        await session.close()


def _create_test_app() -> FastAPI:
    """Create a fresh FastAPI app for testing."""
    from organisms.api.app import create_app

    return create_app()


@pytest.fixture(scope="function")
def app(db: AsyncSession) -> Generator[FastAPI, None, None]:
    """Create test FastAPI app with database session override."""
    from organisms.api.dependencies import get_db

    test_app = _create_test_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    test_app.dependency_overrides[get_db] = override_get_db

    yield test_app

    test_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(app: FastAPI) -> TestClient:
    """Create test client from test app."""
    with TestClient(app) as c:
        yield c
