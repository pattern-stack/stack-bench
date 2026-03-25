"""Event publisher -- single function that fans out to EventBus + EventStore.

Producers call ``publish(event)`` and never interact with subsystems directly.
"""

from __future__ import annotations

from pattern_stack.atoms.shared.events import (
    EventCategory,
    EventData,
    get_event_bus,
    get_event_store,
)

from .topics import DomainBusEvent, DomainEvent


async def publish(event: DomainEvent) -> None:
    """Publish a domain event to the EventBus and EventStore."""
    bus = get_event_bus()
    store = get_event_store()

    # Real-time delivery via concrete DomainBusEvent subclass
    await bus.publish(DomainBusEvent.from_domain_event(event))

    # Persistent record
    await store.emit(
        EventData(
            event_category=EventCategory.BUSINESS,
            event_type=event.topic,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            metadata=event.payload,
        )
    )
