"""Tests for merge cascade REST endpoints on the stacks router."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from organisms.api.app import app
from organisms.api.dependencies import get_stack_api


@pytest.fixture
def stack_id():
    return uuid4()


@pytest.fixture
def cascade_id():
    return uuid4()


@pytest.fixture
def mock_stack_api():
    """Override get_stack_api dependency to return a mock StackAPI."""
    mock_api = AsyncMock()
    mock_api.start_merge_cascade = AsyncMock(
        return_value={
            "cascade": {"id": str(uuid4()), "state": "running"},
            "steps": [],
        }
    )
    mock_api.get_cascade_detail = AsyncMock(
        return_value={
            "cascade": {"id": str(uuid4()), "state": "running"},
            "steps": [],
        }
    )
    mock_api.cancel_cascade = AsyncMock(
        return_value={
            "cascade": {"id": str(uuid4()), "state": "cancelled"},
            "steps": [],
        }
    )

    app.dependency_overrides[get_stack_api] = lambda: mock_api
    yield mock_api
    app.dependency_overrides.pop(get_stack_api, None)


@pytest.mark.unit
async def test_start_cascade_returns_201(stack_id, mock_stack_api) -> None:
    """POST /{stack_id}/merge-cascade returns 201 and calls start_merge_cascade."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/stacks/{stack_id}/merge-cascade",
            json={"merge_method": "squash"},
        )
    assert response.status_code == 201
    mock_stack_api.start_merge_cascade.assert_awaited_once_with(stack_id, triggered_by="api")


@pytest.mark.unit
async def test_start_cascade_default_merge_method(stack_id, mock_stack_api) -> None:
    """POST with empty body uses default merge_method."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/stacks/{stack_id}/merge-cascade",
            json={},
        )
    assert response.status_code == 201
    mock_stack_api.start_merge_cascade.assert_awaited_once()


@pytest.mark.unit
async def test_get_cascade_detail(stack_id, cascade_id, mock_stack_api) -> None:
    """GET /{stack_id}/merge-cascade/{cascade_id} returns cascade detail."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/stacks/{stack_id}/merge-cascade/{cascade_id}")
    assert response.status_code == 200
    mock_stack_api.get_cascade_detail.assert_awaited_once_with(cascade_id)


@pytest.mark.unit
async def test_cancel_cascade(stack_id, cascade_id, mock_stack_api) -> None:
    """POST /{stack_id}/merge-cascade/{cascade_id}/cancel cancels cascade."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/stacks/{stack_id}/merge-cascade/{cascade_id}/cancel")
    assert response.status_code == 200
    mock_stack_api.cancel_cascade.assert_awaited_once_with(cascade_id)


@pytest.mark.unit
async def test_deprecated_merge_returns_410(stack_id, mock_stack_api) -> None:
    """POST /{stack_id}/merge returns 410 Gone pointing to new endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/stacks/{stack_id}/merge")
    assert response.status_code == 410
    data = response.json()
    assert "merge-cascade" in data["detail"]
