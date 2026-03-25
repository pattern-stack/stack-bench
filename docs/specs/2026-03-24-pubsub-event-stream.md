---
title: PubSub Event Stream
date: 2026-03-24
status: draft
branch:
depends_on: []
adrs: []
---

# PubSub Event Stream

## Goal

Build an in-process PubSub event stream system that signals when synced entities change (incoming from GitHub) and when local actions need to be pushed outward (outgoing to GitHub). This enables real-time frontend updates via SSE, decouples sync producers from consumers, and provides a foundation for multi-provider support (Linear, etc.) later. The system is built entirely on pattern-stack's existing EventBus and Broadcast subsystems -- no new infrastructure.

## Context and Motivation

Today, Stack Bench sync operations (sync_stack, merge_stack, create_comment) execute as synchronous request-response flows. The caller gets a result, but nothing else in the system knows something changed. This creates three problems:

1. **No real-time frontend updates.** The frontend must poll or manually refetch after every action. When a sync updates 5 branches and 3 PRs, the UI has no way to know.

2. **Tight coupling in the molecule layer.** `StackAPI.merge_stack` directly calls `github.merge_pr`, transitions state, and commits -- all inline. Adding side effects (invalidate cache, notify frontend, trigger cascade) means editing the same method.

3. **No audit trail for sync operations.** When did we last sync? What changed? Did the outgoing merge succeed? There is no record beyond the database row's `updated_at`.

## Architecture Decision

### Use pattern-stack's existing subsystems, not a custom PubSub

Pattern-stack already provides three event primitives:

| Subsystem | Purpose | Persistence | Delivery |
|-----------|---------|-------------|----------|
| **EventStore** | Persistent event log, queryable | Database or memory | Query-based |
| **EventBus** | In-process pub/sub | None (ephemeral) | Push to registered handlers |
| **Broadcast** | Client-facing real-time pub/sub | None | Push to channel subscribers |

The PubSub system composes all three:

- **EventBus** is the internal backbone. Producers publish domain events. Handlers subscribe. All in-process, zero new infrastructure.
- **EventStore** records events persistently for audit, debugging, and replay. Every event published to the bus is also recorded in the store.
- **Broadcast** pushes events to frontend clients via SSE. A single EventBus subscriber bridges events to the Broadcast subsystem, which manages channel subscriptions.

### Why not a message queue (Redis Pub/Sub, SQS, etc.)?

Stack Bench is a single-user developer workbench. There is one backend process. In-process EventBus with memory backend is sufficient. The pattern-stack subsystems support Redis backends for Broadcast and database backends for EventStore, so scaling up later requires only configuration changes, not code changes.

### Why not use the Jobs subsystem?

Jobs are for durable async work with retries (e.g., running an agent). PubSub events are ephemeral notifications -- "something happened, react if you care." Different tools for different problems. A PubSub handler *may* enqueue a job (e.g., a `pr.merged` event triggers a merge cascade job), but the event itself is not a job.

### Event flow

```
Producer (sync, merge, comment, etc.)
    |
    v
EventBus.publish(Event)  -----> EventStore.record(EventData)
    |                               (persistent audit log)
    |
    v
Registered handlers
    |
    +---> BroadcastBridge --> Broadcast.broadcast(channel, type, payload)
    |                              |
    |                              v
    |                         SSE endpoint --> Frontend
    |
    +---> CacheInvalidator --> cache.delete(relevant keys)
    |
    +---> (future) CascadeTrigger --> job_queue.enqueue(...)
```

## Domain Model

### Event Topics

Events follow a `{entity}.{action}` naming convention. The entity matches the `Pattern.entity` value from the model.

#### Incoming events (GitHub -> local DB changed)

These fire when sync operations update local entities from external data.

| Topic | Trigger | Payload |
|-------|---------|---------|
| `sync.stack.completed` | `StackEntity.sync_stack` finishes | `{stack_id, synced_count, created_count, branch_ids}` |
| `branch.synced` | Branch created or updated during sync | `{branch_id, stack_id, action: "created"\|"updated", head_sha}` |
| `pull_request.synced` | PR created or linked during sync | `{pull_request_id, branch_id, action: "created"\|"linked", external_id}` |
| `check_run.synced` | Check run data updated from GitHub | `{check_run_id, pull_request_id, status, conclusion}` |
| `review_comment.synced` | Comment synced from GitHub | `{comment_id, pull_request_id, author}` |

#### Outgoing events (local action -> needs GitHub push)

These fire when local actions mutate state that should be reflected externally.

| Topic | Trigger | Payload |
|-------|---------|---------|
| `pull_request.merged` | `StackAPI.merge_stack` merges a PR | `{pull_request_id, branch_id, stack_id, external_id}` |
| `pull_request.marked_ready` | PR draft status removed | `{pull_request_id, external_id}` |
| `review_comment.created` | User creates a local comment | `{comment_id, pull_request_id, branch_id}` |
| `review_comment.updated` | User edits/resolves a comment | `{comment_id, resolved}` |
| `merge_cascade.started` | Merge cascade begins | `{cascade_id, stack_id}` |
| `merge_cascade.step_completed` | One cascade step finishes | `{cascade_id, step_id, branch_id, status}` |

### Event Payload Structure

All events share a common envelope:

```python
@dataclass
class DomainEvent:
    topic: str                    # e.g., "pull_request.merged"
    entity_type: str              # e.g., "pull_request"
    entity_id: UUID               # the primary entity's ID
    timestamp: datetime           # UTC
    payload: dict[str, Any]       # topic-specific data
    correlation_id: str | None    # groups related events (e.g., sync batch)
    source: str                   # "sync" | "user_action" | "cascade" | "system"
```

This maps directly to pattern-stack's `Event(type=topic, data={...})` for EventBus and `EventData(event_type=topic, entity_type=..., entity_id=..., metadata={...})` for EventStore.

### Broadcast Channels

Frontend clients subscribe to channels. Events are routed to channels by entity ownership:

| Channel | Events Routed | Use Case |
|---------|---------------|----------|
| `stack:{stack_id}` | All events for entities within that stack | Stack detail view real-time updates |
| `global` | All events | Cross-stack views, debugging |

## File Tree

```
app/backend/src/
  molecules/
    events/                           # NEW -- event stream module
      __init__.py                     # Export public API
      topics.py                       # Topic constants and DomainEvent dataclass
      publisher.py                    # publish() helper that writes to EventBus + EventStore
      handlers/
        __init__.py
        broadcast_bridge.py           # EventBus -> Broadcast bridge (for SSE)
      setup.py                        # Wire handlers to EventBus at startup

    entities/
      stack_entity.py                 # MODIFY -- publish sync events after sync_stack

    apis/
      stack_api.py                    # MODIFY -- publish events after merge, comment ops

  organisms/
    api/
      app.py                          # MODIFY -- call event setup in lifespan
      routers/
        events.py                     # NEW -- SSE endpoint for real-time event stream

app/backend/__tests__/
  molecules/
    test_event_topics.py              # NEW -- topic constant tests
    test_event_publisher.py           # NEW -- publisher unit tests
    test_broadcast_bridge.py          # NEW -- bridge handler tests
    test_event_setup.py              # NEW -- handler registration tests
  organisms/
    test_event_router.py              # NEW -- SSE endpoint tests
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Event topics, DomainEvent/DomainBusEvent, publisher helper | -- |
| 2 | EventBus + EventStore setup in app lifespan (with teardown) | Phase 1 |
| 3 | Publish events from StackEntity and StackAPI | Phase 2 |
| 4 | Broadcast bridge handler + SSE endpoint | Phase 2 |
| 5 | Tests (unit + integration) | Phases 1-4 |

## Phase Details

### Phase 1: Event Topics and Publisher

**`app/backend/src/molecules/events/topics.py`**

Define topic constants as module-level strings grouped by domain. Using plain strings (not an enum) because topics are open for extension -- new features add new topics without modifying a central enum.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


# --- Sync (incoming) ---
SYNC_STACK_COMPLETED = "sync.stack.completed"
BRANCH_SYNCED = "branch.synced"
PULL_REQUEST_SYNCED = "pull_request.synced"
CHECK_RUN_SYNCED = "check_run.synced"
REVIEW_COMMENT_SYNCED = "review_comment.synced"

# --- Actions (outgoing) ---
PULL_REQUEST_MERGED = "pull_request.merged"
PULL_REQUEST_MARKED_READY = "pull_request.marked_ready"
REVIEW_COMMENT_CREATED = "review_comment.created"
REVIEW_COMMENT_UPDATED = "review_comment.updated"
MERGE_CASCADE_STARTED = "merge_cascade.started"
MERGE_CASCADE_STEP_COMPLETED = "merge_cascade.step_completed"


@dataclass
class DomainEvent:
    """Common envelope for all PubSub events."""

    topic: str
    entity_type: str
    entity_id: UUID
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid4()))


class DomainBusEvent(Event):
    """Concrete EventBus event wrapping a DomainEvent."""

    def __init__(self, domain_event: DomainEvent) -> None:
        super().__init__()
        self._domain_event = domain_event

    @property
    def event_type(self) -> str:
        return self._domain_event.topic

    @property
    def data(self) -> dict[str, Any]:
        return {
            "entity_type": self._domain_event.entity_type,
            "entity_id": str(self._domain_event.entity_id),
            "payload": self._domain_event.payload,
            "source": self._domain_event.source,
            "correlation_id": self._domain_event.correlation_id,
            "timestamp": self._domain_event.timestamp.isoformat(),
            "event_id": self._domain_event.event_id,
        }
```

Note: `Event` from pattern-stack is an abstract dataclass. You must subclass it and implement `event_type` as a property. You cannot instantiate `Event` directly.

**`app/backend/src/molecules/events/publisher.py`**

A single `publish()` function that fans out to both EventBus (real-time) and EventStore (persistent). This is the only function producers call.

```python
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
    await bus.publish(DomainBusEvent(event))

    # Persistent record
    await store.emit(EventData(
        event_category=EventCategory.BUSINESS,
        event_type=event.topic,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        metadata=event.payload,
    ))
```

**`app/backend/src/molecules/events/__init__.py`**

```python
from .publisher import publish
from .topics import (
    BRANCH_SYNCED,
    CHECK_RUN_SYNCED,
    MERGE_CASCADE_STARTED,
    MERGE_CASCADE_STEP_COMPLETED,
    PULL_REQUEST_MERGED,
    PULL_REQUEST_MARKED_READY,
    PULL_REQUEST_SYNCED,
    REVIEW_COMMENT_CREATED,
    REVIEW_COMMENT_SYNCED,
    REVIEW_COMMENT_UPDATED,
    SYNC_STACK_COMPLETED,
    DomainBusEvent,
    DomainEvent,
)
```

### Phase 2: Subsystem Setup in App Lifespan

**Modify `app/backend/src/organisms/api/app.py`**

Add EventBus, EventStore, and Broadcast configuration to the lifespan. Then call the handler wiring function.

```python
from molecules.events.setup import setup_event_handlers, teardown_event_handlers

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ... existing engine/session setup ...

    # Event subsystems (auto-configure from settings)
    setup_event_handlers()

    yield

    # Clean up event handlers
    teardown_event_handlers()
    # ... existing shutdown ...
```

**`app/backend/src/molecules/events/setup.py`**

```python
from pattern_stack.atoms.shared.events import get_event_bus

from .handlers.broadcast_bridge import handle_for_broadcast
from . import topics

# All domain event topics that should be forwarded to the broadcast bridge
ALL_TOPICS = [
    topics.SYNC_STACK_COMPLETED,
    topics.BRANCH_SYNCED,
    topics.PULL_REQUEST_SYNCED,
    topics.CHECK_RUN_SYNCED,
    topics.REVIEW_COMMENT_SYNCED,
    topics.PULL_REQUEST_MERGED,
    topics.PULL_REQUEST_MARKED_READY,
    topics.REVIEW_COMMENT_CREATED,
    topics.REVIEW_COMMENT_UPDATED,
    topics.MERGE_CASCADE_STARTED,
    topics.MERGE_CASCADE_STEP_COMPLETED,
]


def setup_event_handlers() -> None:
    """Register all event handlers with the EventBus."""
    bus = get_event_bus()

    for topic in ALL_TOPICS:
        bus.subscribe(topic, handle_for_broadcast)


def teardown_event_handlers() -> None:
    """Clear all EventBus handlers. Called on shutdown."""
    bus = get_event_bus()
    bus.clear()
```

### Phase 3: Publish Events from Existing Code

**Modify `app/backend/src/molecules/entities/stack_entity.py`**

Add event publishing to `sync_stack`. Events are published after the data operations but before the method returns (the caller commits the transaction).

```python
from molecules.events import publish, DomainEvent, SYNC_STACK_COMPLETED, BRANCH_SYNCED, PULL_REQUEST_SYNCED

# Inside sync_stack, after the reconciliation loop:
correlation_id = str(uuid4())

for bd in branches_data:
    # ... existing create/update logic ...

    await publish(DomainEvent(
        topic=BRANCH_SYNCED,
        entity_type="branch",
        entity_id=branch.id,
        source="sync",
        correlation_id=correlation_id,
        payload={
            "stack_id": str(stack_id),
            "action": "created" if was_created else "updated",
            "head_sha": branch.head_sha,
        },
    ))

    if pr_was_created or pr_was_linked:
        await publish(DomainEvent(
            topic=PULL_REQUEST_SYNCED,
            entity_type="pull_request",
            entity_id=pr.id,
            source="sync",
            correlation_id=correlation_id,
            payload={
                "branch_id": str(branch.id),
                "action": "created" if pr_was_created else "linked",
                "external_id": pr.external_id,
            },
        ))

# After the loop:
await publish(DomainEvent(
    topic=SYNC_STACK_COMPLETED,
    entity_type="stack",
    entity_id=stack_id,
    source="sync",
    correlation_id=correlation_id,
    payload={
        "synced_count": synced_count,
        "created_count": created_count,
        "branch_ids": [str(b["branch"].id) for b in branch_results],
    },
))
```

**Modify `app/backend/src/molecules/apis/stack_api.py`**

Add event publishing to `merge_stack`, `create_comment`, `update_comment`.

```python
from molecules.events import publish, DomainEvent, PULL_REQUEST_MERGED, REVIEW_COMMENT_CREATED

# In merge_stack, after each PR is merged:
await publish(DomainEvent(
    topic=PULL_REQUEST_MERGED,
    entity_type="pull_request",
    entity_id=pr.id,
    source="user_action",
    payload={
        "branch_id": str(branch.id),
        "stack_id": str(stack_id),
        "external_id": pr.external_id,
    },
))

# In create_comment, after commit:
await publish(DomainEvent(
    topic=REVIEW_COMMENT_CREATED,
    entity_type="review_comment",
    entity_id=comment.id,
    source="user_action",
    payload={
        "pull_request_id": str(data.pull_request_id),
        "branch_id": str(data.branch_id),
    },
))
```

### Phase 4: Broadcast Bridge and SSE Endpoint

**`app/backend/src/molecules/events/handlers/broadcast_bridge.py`**

This handler receives EventBus events and forwards them to the Broadcast subsystem, which manages channel subscriptions for SSE clients.

Note: `BroadcastHandler` signature is `(event_type: str, payload: dict) -> Awaitable[None]` (two args). The EventBus handler signature is `(event: Event) -> None`. These are different — the bridge translates between them.

```python
from pattern_stack.atoms.broadcast import get_broadcast

from molecules.events.topics import DomainBusEvent


async def handle_for_broadcast(event: DomainBusEvent) -> None:
    """Bridge EventBus events to Broadcast channels for SSE delivery."""
    broadcast = get_broadcast()
    data = event.data

    # Always broadcast to global channel (broadcast.broadcast calls handlers with (event_type, payload))
    await broadcast.broadcast("global", event.event_type, data)

    # Route to entity-specific channels based on payload
    payload = data.get("payload", {})

    if "stack_id" in payload:
        stack_id = payload["stack_id"]
        await broadcast.broadcast(f"stack:{stack_id}", event.event_type, data)
```

**`app/backend/src/organisms/api/routers/events.py`**

SSE endpoint using FastAPI's `StreamingResponse`. Clients connect with a channel parameter and receive a stream of server-sent events.

```python
import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Query
from starlette.responses import StreamingResponse

from pattern_stack.atoms.broadcast import get_broadcast

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream")
async def event_stream(
    channel: str = Query("global", description="Channel to subscribe to"),
) -> StreamingResponse:
    """SSE endpoint for real-time event delivery."""

    async def generate() -> AsyncGenerator[str, None]:
        broadcast = get_broadcast()
        queue: asyncio.Queue[dict] = asyncio.Queue()

        # BroadcastHandler signature is (event_type: str, payload: dict)
        async def on_event(event_type: str, payload: dict) -> None:
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
            # Note: broadcast.unsubscribe(channel, on_event) passes the specific
            # handler reference so only this client is removed, not all subscribers.
            # If the broadcast backend doesn't support per-handler unsubscribe,
            # use broadcast.unsubscribe(channel) and accept the limitation for now.
            await broadcast.unsubscribe(channel, on_event)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

**Modify `app/backend/src/organisms/api/app.py`**

Register the events router:

```python
from organisms.api.routers.events import router as events_router

app.include_router(events_router, prefix="/api/v1")
```

### Phase 5: Tests

**`app/backend/__tests__/molecules/test_event_topics.py`**

```python
import pytest
from molecules.events.topics import DomainEvent, SYNC_STACK_COMPLETED
from uuid import uuid4

@pytest.mark.unit
def test_domain_event_defaults():
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
def test_domain_event_with_payload():
    eid = uuid4()
    event = DomainEvent(
        topic="branch.synced",
        entity_type="branch",
        entity_id=eid,
        payload={"stack_id": str(uuid4()), "action": "created"},
        source="sync",
        correlation_id="batch-123",
    )
    assert event.entity_id == eid
    assert event.payload["action"] == "created"
    assert event.source == "sync"
```

**`app/backend/__tests__/molecules/test_event_publisher.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from molecules.events.publisher import publish
from molecules.events.topics import DomainBusEvent, DomainEvent, BRANCH_SYNCED

@pytest.mark.unit
async def test_publish_sends_to_bus_and_store():
    mock_bus = AsyncMock()
    mock_store = AsyncMock()

    with patch("molecules.events.publisher.get_event_bus", return_value=mock_bus), \
         patch("molecules.events.publisher.get_event_store", return_value=mock_store):

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
```

**`app/backend/__tests__/molecules/test_broadcast_bridge.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from molecules.events.handlers.broadcast_bridge import handle_for_broadcast
from molecules.events.topics import DomainBusEvent, DomainEvent, BRANCH_SYNCED, REVIEW_COMMENT_CREATED
from uuid import uuid4

def _make_bus_event(topic: str, payload: dict) -> DomainBusEvent:
    """Helper to create a DomainBusEvent for testing."""
    return DomainBusEvent(DomainEvent(
        topic=topic,
        entity_type=topic.split(".")[0],
        entity_id=uuid4(),
        payload=payload,
    ))

@pytest.mark.unit
async def test_broadcast_bridge_sends_to_global_and_stack_channels():
    mock_broadcast = AsyncMock()

    with patch("molecules.events.handlers.broadcast_bridge.get_broadcast", return_value=mock_broadcast):
        event = _make_bus_event(BRANCH_SYNCED, {"stack_id": "abc-123", "action": "created"})
        await handle_for_broadcast(event)

        # Should broadcast to global and stack-specific channels
        assert mock_broadcast.broadcast.call_count == 2
        calls = mock_broadcast.broadcast.call_args_list
        # broadcast.broadcast(channel, event_type, data) -- 3 positional args
        channels = {c[0][0] for c in calls}
        assert "global" in channels
        assert "stack:abc-123" in channels
        # Verify event_type is passed correctly
        for call in calls:
            assert call[0][1] == BRANCH_SYNCED

@pytest.mark.unit
async def test_broadcast_bridge_global_only_when_no_stack_id():
    mock_broadcast = AsyncMock()

    with patch("molecules.events.handlers.broadcast_bridge.get_broadcast", return_value=mock_broadcast):
        event = _make_bus_event(REVIEW_COMMENT_CREATED, {"comment_id": "xyz"})
        await handle_for_broadcast(event)

        mock_broadcast.broadcast.assert_called_once()
        assert mock_broadcast.broadcast.call_args[0][0] == "global"
```

**`app/backend/__tests__/molecules/test_event_setup.py`**

```python
import pytest
from unittest.mock import MagicMock, patch
from molecules.events.setup import setup_event_handlers, teardown_event_handlers, ALL_TOPICS

@pytest.mark.unit
def test_setup_registers_all_topics():
    mock_bus = MagicMock()

    with patch("molecules.events.setup.get_event_bus", return_value=mock_bus):
        setup_event_handlers()

        # One subscribe call per topic
        assert mock_bus.subscribe.call_count == len(ALL_TOPICS)
        registered_topics = {c[0][0] for c in mock_bus.subscribe.call_args_list}
        assert registered_topics == set(ALL_TOPICS)

@pytest.mark.unit
def test_teardown_clears_bus():
    mock_bus = MagicMock()

    with patch("molecules.events.setup.get_event_bus", return_value=mock_bus):
        teardown_event_handlers()
        mock_bus.clear.assert_called_once()
```

**`app/backend/__tests__/organisms/test_event_router.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.unit
def test_event_stream_route_registered():
    from organisms.api.app import app
    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/events/stream" in r for r in routes)
```

## Key Design Decisions

### 1. Compose existing pattern-stack subsystems instead of building custom PubSub

Pattern-stack provides EventBus (in-process pub/sub), EventStore (persistent log), and Broadcast (client channels). The PubSub system is a thin composition layer: a `publish()` function that writes to both, plus a bridge handler that forwards to Broadcast. Zero new infrastructure.

### 2. Events module lives in molecules, not atoms or features

Events are cross-feature business concerns -- a sync event references stacks, branches, and PRs. This places them squarely in the molecules layer. The `molecules/events/` module imports from atoms (EventBus, EventStore, Broadcast) and is consumed by molecule entities/APIs and organism routers.

### 3. Topic strings, not an enum

Topics follow `{entity}.{action}` convention and are defined as module constants. Using strings instead of an enum because the topic space is open -- new features add new topics without modifying a central type. The constants provide IDE autocomplete and catch typos.

### 4. DomainEvent dataclass as the canonical envelope

All events share a common shape (topic, entity_type, entity_id, payload, source, correlation_id, timestamp). This maps cleanly to both EventBus's `Event(type, data)` and EventStore's `EventData(event_type, entity_type, entity_id, metadata)`. The `publish()` function handles the mapping.

### 5. correlation_id groups related events

A single `sync_stack` call produces N `branch.synced` events and one `sync.stack.completed` event. The `correlation_id` links them so consumers can group events from the same operation. Generated once per sync batch, passed through to all events.

### 6. source field distinguishes incoming vs outgoing

Rather than separate topic namespaces for incoming/outgoing, the `source` field on DomainEvent indicates origin: `"sync"` (incoming from GitHub), `"user_action"` (outgoing from local), `"cascade"` (automated merge cascade), `"system"` (default). Consumers filter by source when they care about directionality.

### 7. SSE over WebSocket for frontend delivery

SSE (Server-Sent Events) is simpler for unidirectional server-to-client push. The frontend only needs to *receive* events, not send them. SSE works over regular HTTP, auto-reconnects, and needs no special protocol handling. WebSocket would only be needed if the frontend needed to send events back, which it does not.

### 8. Broadcast channels keyed by stack_id

The primary frontend view is a single stack. Subscribing to `stack:{stack_id}` gives the client exactly the events it needs without filtering a global stream. The `global` channel exists for cross-stack views (project dashboard) and debugging.

### 9. Cache invalidation deferred

GitHub cache keys include SHAs, which are content-addressed and immutable. When a branch gets a new `head_sha` via sync, old cache entries are still valid -- they just refer to old commits. New requests will use new SHAs and miss the cache naturally. A cache invalidation handler can be added as a future EventBus subscriber when derived-cache scenarios arise.

### 10. No new database tables

The EventStore already has its own persistence. The EventBus is ephemeral. The Broadcast is ephemeral. No new Alembic migrations needed. The DomainEvent dataclass is a runtime-only envelope, not a database model.

## Open Questions

1. **Should we add `project_id` to the Broadcast routing?** Currently we route to `stack:{stack_id}` channels. If the frontend needs project-level real-time updates, we would need to resolve stack -> project in the broadcast bridge. Deferring until the project dashboard view exists.

2. **Event replay on SSE reconnect.** When an SSE client reconnects after a disconnect, it misses events. We could use EventStore to replay recent events since a `Last-Event-ID` header. This is a future enhancement -- start with simple reconnect-and-refetch.

3. **Rate limiting event publishing.** A bulk sync of 20 branches produces 20+ events. Should we batch/debounce? For a single-user workbench this is fine. Revisit if event volume becomes a problem.

4. **Per-handler unsubscribe for Broadcast.** The current `broadcast.unsubscribe(channel)` may remove all handlers for a channel. If multiple SSE clients subscribe to the same channel, we need to verify the backend supports per-handler removal via `unsubscribe(channel, handler)`. If not, a wrapper layer that manages per-client subscriptions is needed.
