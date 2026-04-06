"""Bridge EventBus events to Broadcast channels for SSE delivery.

The EventBus handler receives ``DomainBusEvent`` instances.  This handler
extracts the data and forwards it to the Broadcast subsystem so SSE-connected
clients receive real-time updates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pattern_stack.atoms.broadcast import get_broadcast

if TYPE_CHECKING:
    from pattern_stack.atoms.shared.events import Event


async def handle_for_broadcast(event: Event) -> None:
    """Bridge EventBus events to Broadcast channels for SSE delivery."""
    broadcast = get_broadcast()
    # All events on our topics are DomainBusEvent instances which expose .data
    data: dict[str, Any] = cast("Any", event).data

    # Always broadcast to the global channel
    await broadcast.broadcast("global", event.event_type, data)

    # Route to stack-specific channel when payload contains stack_id
    payload = data.get("payload", {})
    if isinstance(payload, dict) and "stack_id" in payload:
        stack_id = payload["stack_id"]
        await broadcast.broadcast(f"stack:{stack_id}", event.event_type, data)

    # Route to conversation-specific channel when payload contains conversation_id
    if isinstance(payload, dict) and "conversation_id" in payload:
        conv_id = payload["conversation_id"]
        await broadcast.broadcast(f"conversation:{conv_id}", event.event_type, data)
