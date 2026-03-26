"""Tests for the SSE event stream router."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from organisms.api.app import create_app


@pytest.mark.unit
def test_event_stream_route_registered() -> None:
    """Verify the /events/stream route is present in the app."""
    app = create_app()
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/events/stream" in r for r in routes)


@pytest.mark.unit
def test_event_history_route_registered() -> None:
    """Verify the /events/history route is present in the app."""
    app = create_app()
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/events/history" in r for r in routes)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_backpressure_drops_oldest_events() -> None:
    """When the SSE queue is full, oldest events are dropped."""
    from organisms.api.routers.events import _enqueue_with_backpressure

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=3)

    # Fill the queue
    await _enqueue_with_backpressure(queue, {"event_type": "a", "n": 1})
    await _enqueue_with_backpressure(queue, {"event_type": "b", "n": 2})
    await _enqueue_with_backpressure(queue, {"event_type": "c", "n": 3})

    # Queue is now full — next enqueue should drop oldest
    await _enqueue_with_backpressure(queue, {"event_type": "d", "n": 4})

    # Drain and verify: oldest (a) was dropped
    items = []
    while not queue.empty():
        items.append(await queue.get())

    assert len(items) == 3
    assert items[0]["n"] == 2  # b
    assert items[1]["n"] == 3  # c
    assert items[2]["n"] == 4  # d


@pytest.mark.unit
@pytest.mark.asyncio
async def test_history_endpoint_returns_events() -> None:
    """The /events/history endpoint queries the EventStore and returns events."""
    from organisms.api.routers.events import event_history

    mock_event = MagicMock()
    mock_event.event_type = "stack.created"
    mock_event.entity_type = "Stack"
    mock_event.entity_id = uuid4()
    mock_event.event_metadata = {"key": "value"}
    mock_event.timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    mock_store = AsyncMock()
    mock_store.query = AsyncMock(return_value=[mock_event])

    with patch(
        "organisms.api.routers.events.get_event_store", return_value=mock_store
    ):
        result = await event_history(entity_type="Stack", event_type=None, limit=50)

    assert len(result) == 1
    assert result[0]["event_type"] == "stack.created"
    assert result[0]["entity_type"] == "Stack"
    assert result[0]["entity_id"] == str(mock_event.entity_id)
    assert result[0]["metadata"] == {"key": "value"}
    assert result[0]["timestamp"] == "2026-01-01T00:00:00+00:00"

    # Verify query was called with EventFilters
    mock_store.query.assert_called_once()
    filters = mock_store.query.call_args[0][0]
    assert filters.entity_type == "Stack"
    assert filters.limit == 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_history_endpoint_default_params() -> None:
    """The /events/history endpoint works with default parameters."""
    from organisms.api.routers.events import event_history

    mock_store = AsyncMock()
    mock_store.query = AsyncMock(return_value=[])

    with patch(
        "organisms.api.routers.events.get_event_store", return_value=mock_store
    ):
        result = await event_history(entity_type=None, event_type=None, limit=50)

    assert result == []
    filters = mock_store.query.call_args[0][0]
    assert filters.entity_type is None
    assert filters.event_type is None
    assert filters.limit == 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_history_endpoint_error_handling() -> None:
    """The /events/history endpoint handles EventStore errors gracefully."""
    from fastapi import HTTPException

    from organisms.api.routers.events import event_history

    mock_store = AsyncMock()
    mock_store.query = AsyncMock(side_effect=Exception("DB connection failed"))

    with patch(
        "organisms.api.routers.events.get_event_store", return_value=mock_store
    ):
        with pytest.raises(HTTPException) as exc_info:
            await event_history(entity_type=None, event_type=None, limit=50)

    assert exc_info.value.status_code == 500
