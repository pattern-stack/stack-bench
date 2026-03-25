"""Tests for the event publisher."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from molecules.events.publisher import publish
from molecules.events.topics import BRANCH_SYNCED, DomainBusEvent, DomainEvent


@pytest.mark.unit
async def test_publish_sends_to_bus_and_store() -> None:
    """publish() fans out to EventBus and EventStore."""
    mock_bus = AsyncMock()
    mock_store = AsyncMock()

    with (
        patch("molecules.events.publisher.get_event_bus", return_value=mock_bus),
        patch("molecules.events.publisher.get_event_store", return_value=mock_store),
    ):
        event = DomainEvent(
            topic=BRANCH_SYNCED,
            entity_type="branch",
            entity_id=uuid4(),
            payload={"action": "created"},
        )
        await publish(event)

        mock_bus.publish.assert_called_once()
        mock_store.emit.assert_called_once()

        # Verify bus event is a DomainBusEvent with correct event_type
        bus_event = mock_bus.publish.call_args[0][0]
        assert isinstance(bus_event, DomainBusEvent)
        assert bus_event.event_type == BRANCH_SYNCED
        assert bus_event.data["entity_type"] == "branch"

        # Verify store event has correct metadata
        store_call = mock_store.emit.call_args[0][0]
        assert store_call.event_type == BRANCH_SYNCED
        assert store_call.entity_type == "branch"
