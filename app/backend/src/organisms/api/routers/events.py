"""SSE endpoint for real-time event delivery.

Clients connect to ``/events/stream?channel=global`` (or ``stack:{id}``) and
receive a stream of server-sent events.  A keepalive comment is sent every
30 seconds to prevent proxy timeouts.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Query
from pattern_stack.atoms.broadcast import get_broadcast
from pattern_stack.atoms.shared.events import EventFilters, get_event_store
from starlette.responses import StreamingResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

# Maximum queued events per SSE client before backpressure kicks in.
_MAX_QUEUE_SIZE = 100


async def _enqueue_with_backpressure(
    queue: asyncio.Queue[dict[str, Any]],
    event: dict[str, Any],
) -> None:
    """Add *event* to *queue*, dropping the oldest item if the queue is full."""
    if queue.full():
        try:
            queue.get_nowait()  # discard oldest
        except asyncio.QueueEmpty:
            pass  # race-condition guard
    await queue.put(event)


@router.get("/stream")
async def event_stream(
    channel: str = Query("global", description="Channel to subscribe to"),
) -> StreamingResponse:
    """SSE endpoint for real-time event delivery."""

    async def generate() -> AsyncGenerator[str, None]:
        broadcast = get_broadcast()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=_MAX_QUEUE_SIZE,
        )
        closed = False

        async def on_event(event_type: str, payload: dict[str, Any]) -> None:
            if not closed:
                await _enqueue_with_backpressure(
                    queue, {"event_type": event_type, **payload}
                )

        await broadcast.subscribe(channel, on_event)
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_type = data.pop("event_type", "message")
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            # Mark handler as closed so queued callbacks are dropped.
            # Note: broadcast.unsubscribe(channel) removes ALL handlers for
            # the channel, which would break other SSE clients on the same
            # channel.  For a single-user workbench this is acceptable; a
            # per-handler unsubscribe wrapper can be added later if needed.
            closed = True

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
async def event_history(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    event_type: str | None = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Query historical events from the EventStore."""
    try:
        store = get_event_store()
        filters = EventFilters(
            entity_type=entity_type,
            event_type=event_type,
            limit=limit,
        )
        events = await store.query(filters)
        return [
            {
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": str(e.entity_id),
                "metadata": e.event_metadata if hasattr(e, "event_metadata") else {},
                "timestamp": (
                    e.timestamp.isoformat() if hasattr(e, "timestamp") else None
                ),
            }
            for e in events
        ]
    except Exception:
        logger.exception("Failed to query event history")
        raise HTTPException(
            status_code=500,
            detail="Failed to query event history",
        )
