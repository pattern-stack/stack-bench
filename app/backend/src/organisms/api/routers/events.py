"""SSE endpoint for real-time event delivery.

Clients connect to ``/events/stream?channel=global`` (or ``stack:{id}``) and
receive a stream of server-sent events.  A keepalive comment is sent every
30 seconds to prevent proxy timeouts.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Query
from pattern_stack.atoms.broadcast import get_broadcast
from starlette.responses import StreamingResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream")
async def event_stream(
    channel: str = Query("global", description="Channel to subscribe to"),
) -> StreamingResponse:
    """SSE endpoint for real-time event delivery."""

    async def generate() -> AsyncGenerator[str, None]:
        broadcast = get_broadcast()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        closed = False

        async def on_event(event_type: str, payload: dict[str, Any]) -> None:
            if not closed:
                await queue.put({"event_type": event_type, **payload})

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
