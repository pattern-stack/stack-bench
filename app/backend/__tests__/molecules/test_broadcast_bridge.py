"""Tests for the broadcast bridge handler."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from molecules.events.handlers.broadcast_bridge import handle_for_broadcast
from molecules.events.topics import (
    BRANCH_SYNCED,
    REVIEW_COMMENT_CREATED,
    DomainBusEvent,
    DomainEvent,
)


def _make_bus_event(topic: str, payload: dict) -> DomainBusEvent:
    """Helper to create a DomainBusEvent for testing."""
    return DomainBusEvent.from_domain_event(
        DomainEvent(
            topic=topic,
            entity_type=topic.split(".")[0],
            entity_id=uuid4(),
            payload=payload,
        )
    )


@pytest.mark.unit
async def test_broadcast_bridge_sends_to_global_and_stack_channels() -> None:
    """Events with stack_id in payload broadcast to both global and stack channels."""
    mock_broadcast = AsyncMock()

    with patch(
        "molecules.events.handlers.broadcast_bridge.get_broadcast",
        return_value=mock_broadcast,
    ):
        event = _make_bus_event(BRANCH_SYNCED, {"stack_id": "abc-123", "action": "created"})
        await handle_for_broadcast(event)

        # Should broadcast to global and stack-specific channels
        assert mock_broadcast.broadcast.call_count == 2
        calls = mock_broadcast.broadcast.call_args_list
        channels = {c[0][0] for c in calls}
        assert "global" in channels
        assert "stack:abc-123" in channels

        # Verify event_type is passed correctly
        for call in calls:
            assert call[0][1] == BRANCH_SYNCED


@pytest.mark.unit
async def test_broadcast_bridge_global_only_when_no_stack_id() -> None:
    """Events without stack_id in payload only broadcast to global."""
    mock_broadcast = AsyncMock()

    with patch(
        "molecules.events.handlers.broadcast_bridge.get_broadcast",
        return_value=mock_broadcast,
    ):
        event = _make_bus_event(REVIEW_COMMENT_CREATED, {"comment_id": "xyz"})
        await handle_for_broadcast(event)

        mock_broadcast.broadcast.assert_called_once()
        assert mock_broadcast.broadcast.call_args[0][0] == "global"
