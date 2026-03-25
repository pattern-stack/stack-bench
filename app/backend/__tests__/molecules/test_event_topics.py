"""Tests for event topics and DomainEvent envelope."""

from uuid import uuid4

import pytest

from molecules.events.topics import (
    BRANCH_SYNCED,
    SYNC_STACK_COMPLETED,
    DomainBusEvent,
    DomainEvent,
)


@pytest.mark.unit
def test_domain_event_defaults() -> None:
    """DomainEvent populates defaults for source, correlation_id, timestamp, event_id."""
    event = DomainEvent(
        topic=SYNC_STACK_COMPLETED,
        entity_type="stack",
        entity_id=uuid4(),
    )
    assert event.source == "system"
    assert event.correlation_id is None
    assert event.timestamp is not None
    assert event.event_id is not None


@pytest.mark.unit
def test_domain_event_with_payload() -> None:
    """DomainEvent stores custom payload and source."""
    eid = uuid4()
    event = DomainEvent(
        topic=BRANCH_SYNCED,
        entity_type="branch",
        entity_id=eid,
        payload={"stack_id": str(uuid4()), "action": "created"},
        source="sync",
        correlation_id="batch-123",
    )
    assert event.entity_id == eid
    assert event.payload["action"] == "created"
    assert event.source == "sync"
    assert event.correlation_id == "batch-123"


@pytest.mark.unit
def test_domain_bus_event_from_domain_event() -> None:
    """DomainBusEvent wraps a DomainEvent with correct event_type and data."""
    eid = uuid4()
    domain = DomainEvent(
        topic=BRANCH_SYNCED,
        entity_type="branch",
        entity_id=eid,
        payload={"action": "updated"},
        source="sync",
    )
    bus_event = DomainBusEvent.from_domain_event(domain)

    assert bus_event.event_type == BRANCH_SYNCED
    assert bus_event.data["entity_type"] == "branch"
    assert bus_event.data["entity_id"] == str(eid)
    assert bus_event.data["payload"] == {"action": "updated"}
    assert bus_event.data["source"] == "sync"
    assert bus_event.data["event_id"] == domain.event_id
    assert bus_event.data["timestamp"] == domain.timestamp.isoformat()


@pytest.mark.unit
def test_domain_bus_event_inherits_event_id_and_timestamp() -> None:
    """DomainBusEvent carries over event_id and timestamp from the DomainEvent."""
    domain = DomainEvent(
        topic=SYNC_STACK_COMPLETED,
        entity_type="stack",
        entity_id=uuid4(),
    )
    bus_event = DomainBusEvent.from_domain_event(domain)

    assert bus_event.event_id == domain.event_id
    assert bus_event.timestamp == domain.timestamp
