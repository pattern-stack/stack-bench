---
title: Event Stream and Subsystem Wiring
date: 2026-03-24
status: in-progress
branch: dugshub/ep012-event-subsystem/1-ep-012-event-stream-subsystem-wiring
depends_on: []
adrs: []
epic: "EP-012 (#179)"
issues: ["#180 (SB-071)", "#181 (SB-072)", "#182 (SB-073)", "#183 (SB-074)", "#184 (SB-075)", "#185 (SB-076)"]
---

# Event Stream and Subsystem Wiring

## Goal

Wire the existing Stack Bench backend to pattern-stack's three event subsystems (EventStore, EventBus, Broadcast) and the Jobs subsystem. Eleven models already declare `emit_state_transitions = True` but nothing consumes those signals. This spec designs the plumbing: persistent audit trail via EventStore, in-process reactive handlers via EventBus, real-time client push via Broadcast, and async job execution via the framework's JobQueue/Worker replacing the app's ad-hoc job model usage.

## Port Assessment: What Exists vs What Is Missing

### Already in Place

| Component | Status | Notes |
|-----------|--------|-------|
| 23 models across features layer | Complete | All using BasePattern or EventPattern |
| 11 EventPattern models with `emit_state_transitions = True` | Complete | Stack, Branch, PullRequest, MergeCascade, CascadeStep, Conversation, Task, TaskProject, Sprint, ToolCall, Project |
| `system_events` table | Complete | Migration exists in `94f4eb416247_initial_tables.py` |
| Feature services (BaseService) | Complete | One per model, inherited CRUD |
| Molecule entities (StackEntity, ConversationEntity) | Complete | Aggregate roots |
| Molecule APIs (StackAPI, ConversationAPI) | Complete | Facade layer |
| Organism routers | Complete | REST API with FastAPI |
| App `Job` model (features/jobs) | Complete | Domain model for develop jobs with custom states |
| ConversationRunner with SSE streaming | Complete | Already streams agentic-patterns events to clients |

### Missing (What This Spec Builds)

| Component | Status | What Is Needed |
|-----------|--------|----------------|
| EventSystem initialization | Not wired | Call `get_event_system()` / `get_event_store()` in lifespan |
| EventBus handlers | Not wired | Subscribe to state transitions, trigger side effects |
| Broadcast to clients | Not wired | Push state changes to frontend via SSE endpoint |
| Jobs subsystem (framework) | Not wired | `job_records` table missing; Worker not started |
| Event emission from services | Not wired | Services do state transitions but never call EventSystem.emit() |
| SSE event stream endpoint | Not built | Endpoint for frontend to subscribe to real-time updates |
| Event middleware layer | Not built | Molecule-layer component that bridges transitions to EventSystem |

## Architecture

### The Three-Layer Event Flow

```
Model.transition_to("running")
        |
        v
  EventMiddleware (molecule layer)
   |         |           |
   v         v           v
EventStore  EventBus   Broadcast
(persist)   (in-proc)  (to clients)
   |         |           |
   v         v           v
 Audit     Handlers    SSE/WS
 Trail     (side       Endpoint
           effects)
```

### How EventSystem Unifies the Three Components

Pattern-stack provides `EventSystem` as a unified facade. A single `emit()` call:

1. **Persists** the event to EventStore (database-backed `system_events` table) -- audit trail
2. **Publishes** an `EventNotification` to EventBus -- triggers in-process handlers
3. The EventBus handlers can then **broadcast** to clients via the Broadcast subsystem

The `EventSystem.emit()` method uses a behavior resolution hierarchy:
1. Explicit `persist`/`broadcast` parameters (highest priority)
2. `Pattern.event_behavior` configuration on the model class
3. Global defaults by `EventCategory` (all persist+broadcast by default except `CHANGE` which skips broadcast and `UI` which skips persist)

### Subsystem Relationships

```
                    EventSystem
                   /     |      \
                  /      |       \
          EventStore  EventBus  Broadcast
          (database)  (in-proc) (memory/redis)
              |          |          |
              v          v          v
         system_events  handlers   SSE endpoint
         table          (molecules) (organisms)
```

### Jobs Subsystem Integration

The framework's `JobQueue` + `Worker` + `JobRecord` replace ad-hoc job execution. The app's existing `Job` model (features/jobs) remains as the **domain model** -- it tracks develop-job business state (phases, gates, artifacts). The framework's `JobRecord` is the **execution record** -- it tracks queue position, retries, and worker assignment.

```
App Job (domain)          Framework JobRecord (execution)
  queued --------enqueue-------> pending
  running <------dequeue---------  running
  gated   (domain-specific)       (not represented)
  complete ------complete-------> completed
  failed  -------fail-----------> failed
```

The `Job.job_record_id` field (already exists) links the two.

## Event Types: Complete Taxonomy

### Event Naming Convention

`{entity}.{action}` where action is one of:
- State transitions: `{entity}.state.{from_state}.{to_state}` (category: `STATE`)
- Lifecycle: `{entity}.created`, `{entity}.deleted` (category: `LIFECYCLE`)
- Business: `{entity}.{domain_verb}` (category: `BUSINESS`)
- Changes: `{entity}.changed.{field_name}` (category: `CHANGE`)

### Core Domain Events

#### Stack Events
| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `stack.created` | LIFECYCLE | StackEntity.create_stack | -- |
| `stack.deleted` | LIFECYCLE | StackEntity.delete_stack (soft) | -- |
| `stack.state.draft.active` | STATE | First branch pushed | -- |
| `stack.state.active.submitted` | STATE | All PRs submitted | Broadcast to UI |
| `stack.state.submitted.merged` | STATE | All PRs merged | Broadcast to UI |

#### Branch Events
| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `branch.created` | LIFECYCLE | StackEntity.add_branch | -- |
| `branch.state.created.pushed` | STATE | After `st push` sync | Broadcast to UI |
| `branch.state.pushed.reviewing` | STATE | PR opened on GitHub | -- |
| `branch.state.reviewing.ready` | STATE | PR approved | -- |
| `branch.state.ready.submitted` | STATE | PR submitted for merge | -- |
| `branch.state.submitted.merged` | STATE | PR merged | Trigger cascade check |
| `branch.changed.head_sha` | CHANGE | sync_stack updates SHA | Broadcast to UI (needs-restack detection) |

#### PullRequest Events
| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `pull_request.created` | LIFECYCLE | StackEntity.create_pull_request | -- |
| `pull_request.state.draft.open` | STATE | PR marked ready | Broadcast to UI |
| `pull_request.state.open.approved` | STATE | PR approved | Broadcast to UI |
| `pull_request.state.approved.merged` | STATE | PR merged | Trigger merge cascade |
| `pull_request.state.*.closed` | STATE | PR closed | Broadcast to UI |
| `pull_request.changed.external_id` | CHANGE | link_external_pr | -- |

#### MergeCascade Events
| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `merge_cascade.created` | LIFECYCLE | PR merged triggers cascade | Enqueue cascade job |
| `merge_cascade.state.pending.running` | STATE | Worker picks up cascade | Broadcast progress |
| `merge_cascade.state.running.completed` | STATE | All steps done | Broadcast completion |
| `merge_cascade.state.running.failed` | STATE | Step failed | Broadcast failure |

#### CascadeStep Events
| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `cascade_step.state.*.*` | STATE | Step progresses | Broadcast progress |
| `cascade_step.state.*.conflict` | STATE | Rebase conflict | Broadcast, pause cascade |

#### Job Events
| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `job.created` | LIFECYCLE | New develop job | Enqueue to JobQueue |
| `job.state.queued.running` | STATE | Worker starts job | Broadcast progress |
| `job.state.running.complete` | STATE | Job succeeds | Broadcast completion |
| `job.state.running.failed` | STATE | Job fails | Broadcast failure |
| `job.state.running.gated` | STATE | Gate check needed | Broadcast gate prompt |

#### AgentRun Events
| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `agent_run.state.pending.running` | STATE | Agent starts | Broadcast to UI |
| `agent_run.state.running.complete` | STATE | Agent finishes | Update Job token counts |
| `agent_run.state.running.failed` | STATE | Agent errors | Broadcast failure |

#### Conversation Events
| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `conversation.created` | LIFECYCLE | New conversation | -- |
| `conversation.state.created.active` | STATE | First message sent | -- |
| `conversation.state.active.completed` | STATE | Conversation ends | -- |
| `conversation.state.active.failed` | STATE | Error during run | Broadcast failure |

#### Task Events
| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `task.created` | LIFECYCLE | New task | -- |
| `task.state.*.*` | STATE | Task state changes | Broadcast to UI |
| `task.changed.assignee_id` | CHANGE | Task reassigned | -- |
| `task.changed.priority` | CHANGE | Priority changed | -- |

### Business Events (Cross-Cutting)

| Event Type | Category | Trigger | Side Effects |
|-----------|----------|---------|-------------|
| `stack.synced` | BUSINESS | sync_stack completes | Broadcast updated branch list |
| `stack.merged` | BUSINESS | merge_stack completes | Broadcast final results |
| `restack.started` | BUSINESS | RemoteRestackService begins | Broadcast progress |
| `restack.completed` | BUSINESS | Restack finishes | Broadcast new SHAs, trigger sync |
| `restack.conflict` | BUSINESS | Rebase conflict detected | Broadcast conflict details |

## Domain Model

### New Components

| Component | Layer | Type | Purpose |
|-----------|-------|------|---------|
| `EventMiddleware` | molecule | Service class | Bridges model transitions to EventSystem |
| `EventHandlerRegistry` | molecule | Registry | Registers and manages EventBus handlers |
| `SSEStreamRouter` | organism | Router | FastAPI SSE endpoint for real-time events |
| `JobDispatcher` | molecule | Service class | Bridges app Job model to framework JobQueue |
| `configure_subsystems()` | organism | Startup function | Initializes all subsystems in lifespan |

### Existing Components Modified

| Component | Change |
|-----------|--------|
| `app.py` lifespan | Add subsystem initialization |
| `settings.py` | Add EVENT_BACKEND, BROADCAST_BACKEND, JOB_MAX_CONCURRENT |
| `StackEntity` | Emit events after state-changing operations |
| `ConversationEntity` | Emit events after state-changing operations |
| `StackAPI` | Emit business events (synced, merged) |
| `dependencies.py` | Add EventSystem and Broadcast dependencies |

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Subsystem initialization and configuration | -- |
| 2 | EventMiddleware and event emission from entities | Phase 1 |
| 3 | EventBus handler registry and reactive handlers | Phase 2 |
| 4 | SSE broadcast endpoint for real-time UI updates | Phase 1 |
| 5 | Jobs subsystem wiring (JobQueue + Worker) | Phase 1 |
| 6 | Integration tests | Phases 1-5 |

## Phase Details

### Phase 1: Subsystem Initialization and Configuration

Wire up all four subsystems at app startup. No behavior changes yet -- just ensure the singletons are configured and healthy.

**Files to create:**

- `app/backend/src/molecules/events/__init__.py` -- Package init
- `app/backend/src/molecules/events/startup.py` -- `configure_subsystems()` function

**Files to modify:**

- `app/backend/src/config/settings.py` -- Add subsystem settings
- `app/backend/src/organisms/api/app.py` -- Call `configure_subsystems()` in lifespan

**Settings additions:**
```python
# In AppSettings
EVENT_BACKEND: str = Field(default="database")
BROADCAST_BACKEND: str = Field(default="memory")
JOB_MAX_CONCURRENT: int = Field(default=3)
```

**Startup function:**
```python
# molecules/events/startup.py
async def configure_subsystems(session_factory):
    """Initialize all pattern-stack subsystems."""
    # 1. EventStore auto-configures from DATABASE_URL
    store = get_event_store()

    # 2. EventBus is always in-memory (process-local)
    bus = get_event_bus()

    # 3. Broadcast auto-configures from BROADCAST_BACKEND
    broadcast = get_broadcast()

    # 4. Jobs subsystem
    configure_jobs(
        JobConfig(backend="database", max_concurrent=settings.JOB_MAX_CONCURRENT),
        session_factory=session_factory,
    )

    # 5. Register job handlers (Phase 5)
    # queue = get_job_queue()
    # queue.register_handler("develop.run", handle_develop_job)

    # 6. EventSystem singleton
    return get_event_system()
```

**Migration:**

- `app/backend/alembic/versions/XXXX_add_job_records_table.py` -- Create `job_records` table for the framework's JobQueue database backend

### Phase 2: EventMiddleware and Event Emission

Create a molecule-layer middleware that entities call after state transitions. This is the central point where transitions become events.

**Files to create:**

- `app/backend/src/molecules/events/middleware.py` -- EventMiddleware class
- `app/backend/src/molecules/events/types.py` -- Event type constants

**EventMiddleware design:**

```python
# molecules/events/middleware.py
class EventMiddleware:
    """Bridges model state transitions to the EventSystem.

    Entities call this after transition_to() to emit events that are
    persisted to EventStore, published to EventBus, and broadcast to clients.
    """

    def __init__(self, system: EventSystem | None = None):
        self._system = system or get_event_system()

    async def on_state_transition(
        self,
        entity: EventPattern,
        from_state: str,
        to_state: str,
    ) -> None:
        """Emit a STATE event for a model transition."""
        entity_type = entity.Pattern.entity  # e.g., "stack"
        await self._system.emit(
            EventData(
                event_category=EventCategory.STATE,
                event_type=f"{entity_type}.state.{from_state}.{to_state}",
                entity_type=entity_type.title(),
                entity_id=entity.id,
                state_from=from_state,
                state_to=to_state,
            ),
            source=entity,
        )

    async def on_created(self, entity: BasePattern) -> None:
        """Emit a LIFECYCLE created event."""
        entity_type = entity.Pattern.entity
        await self._system.emit(
            EventData(
                event_category=EventCategory.LIFECYCLE,
                event_type=f"{entity_type}.created",
                entity_type=entity_type.title(),
                entity_id=entity.id,
            ),
            source=entity,
        )

    async def on_deleted(self, entity: BasePattern) -> None:
        """Emit a LIFECYCLE deleted event."""
        entity_type = entity.Pattern.entity
        await self._system.emit(
            EventData(
                event_category=EventCategory.LIFECYCLE,
                event_type=f"{entity_type}.deleted",
                entity_type=entity_type.title(),
                entity_id=entity.id,
            ),
            source=entity,
        )

    async def on_business_event(
        self,
        event_type: str,
        entity: BasePattern,
        metadata: dict | None = None,
    ) -> None:
        """Emit a BUSINESS event for domain operations."""
        entity_type_name = entity.Pattern.entity
        await self._system.emit(
            EventData(
                event_category=EventCategory.BUSINESS,
                event_type=event_type,
                entity_type=entity_type_name.title(),
                entity_id=entity.id,
                metadata=metadata or {},
            ),
            source=entity,
        )

    async def on_field_changed(
        self,
        entity: BasePattern,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Emit a CHANGE event for a field update."""
        entity_type = entity.Pattern.entity
        await self._system.emit(
            EventData(
                event_category=EventCategory.CHANGE,
                event_type=f"{entity_type}.changed.{field_name}",
                entity_type=entity_type.title(),
                entity_id=entity.id,
                field_name=field_name,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            ),
            source=entity,
        )
```

**Entity modifications:**

Add `EventMiddleware` to `StackEntity` and `ConversationEntity`. Example for StackEntity:

```python
class StackEntity:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.events = EventMiddleware()
        # ... existing services ...

    async def create_stack(self, ...) -> Stack:
        stack = await self.stack_service.create(...)
        await self.events.on_created(stack)
        return stack
```

State transitions in `StackAPI.merge_stack()` would emit:

```python
pr.transition_to("approved")
await self.entity.events.on_state_transition(pr, "open", "approved")
pr.transition_to("merged")
await self.entity.events.on_state_transition(pr, "approved", "merged")
```

### Phase 3: EventBus Handler Registry and Reactive Handlers

Register handlers that respond to events published on the EventBus. These implement the reactive side effects (e.g., "when a PR merges, start a cascade").

**Files to create:**

- `app/backend/src/molecules/events/handlers.py` -- Handler functions
- `app/backend/src/molecules/events/registry.py` -- Handler registration

**Handler registry design:**

```python
# molecules/events/registry.py
def register_event_handlers(bus: EventBus) -> None:
    """Register all event handlers on the EventBus."""

    # Stack lifecycle
    bus.on("branch.state.submitted.merged", on_branch_merged)
    bus.on("merge_cascade.state.running.completed", on_cascade_completed)
    bus.on("merge_cascade.state.running.failed", on_cascade_failed)
    bus.on("job.state.queued.running", on_job_started)

    # Broadcast bridge -- forward state events to Broadcast for SSE
    bus.on("*", broadcast_bridge)
```

**Key handlers:**

```python
# molecules/events/handlers.py

async def on_branch_merged(event: EventNotification) -> None:
    """When a branch merges, check if cascade is needed."""
    # Look up stack, determine if next branch needs retargeting
    pass

async def broadcast_bridge(event: EventNotification) -> None:
    """Forward EventBus notifications to Broadcast for client delivery."""
    broadcast = get_broadcast()
    channel = event.entity_type.lower() if event.entity_type else "system"
    await broadcast.broadcast(
        channel=channel,
        event_type=event.type,
        payload={
            "entity_id": str(event.entity_id) if event.entity_id else None,
            "entity_type": event.entity_type,
            "metadata": event.metadata,
            "timestamp": event.timestamp.isoformat(),
        },
    )
```

**Called from startup:**

```python
# In configure_subsystems()
bus = get_event_bus()
register_event_handlers(bus)
```

### Phase 4: SSE Broadcast Endpoint

Create a FastAPI SSE endpoint that clients subscribe to. The endpoint uses the Broadcast subsystem to receive events and streams them as Server-Sent Events.

**Files to create:**

- `app/backend/src/organisms/api/routers/events.py` -- SSE stream router

**SSE endpoint design:**

```python
# organisms/api/routers/events.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/events", tags=["events"])

@router.get("/stream")
async def event_stream(
    channels: str = Query("stack,branch,pull_request,job"),
) -> StreamingResponse:
    """SSE endpoint for real-time event updates.

    Clients connect and receive events for the specified channels.
    Channels correspond to entity types (stack, branch, pull_request, etc).
    """
    channel_list = [c.strip() for c in channels.split(",")]

    async def generate():
        broadcast = get_broadcast()
        queue = asyncio.Queue()

        async def handler(event_type: str, payload: dict):
            await queue.put((event_type, payload))

        for channel in channel_list:
            await broadcast.subscribe(channel, handler)

        try:
            while True:
                event_type, payload = await queue.get()
                data = json.dumps({"type": event_type, **payload})
                yield f"event: {event_type}\ndata: {data}\n\n"
        finally:
            for channel in channel_list:
                await broadcast.unsubscribe(channel)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

@router.get("/history")
async def event_history(
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    limit: int = Query(50, le=200),
) -> list[dict]:
    """Query historical events for an entity from EventStore."""
    store = get_event_store()
    events = await store.query(
        EventFilters(entity_type=entity_type, entity_id=entity_id),
    )
    return [e.to_dict() for e in events[:limit]]
```

**Register in app.py:**

```python
from organisms.api.routers.events import router as events_router
app.include_router(events_router, prefix="/api/v1")
```

### Phase 5: Jobs Subsystem Wiring

Wire the framework's `JobQueue` + `Worker` to execute long-running operations. The app's `Job` model remains the domain model; the framework's `JobRecord` is the execution queue.

**Files to create:**

- `app/backend/src/molecules/events/job_handlers.py` -- Job handler functions
- `app/backend/src/molecules/events/job_dispatcher.py` -- Dispatcher to enqueue jobs

**Migration:**

- `app/backend/alembic/versions/XXXX_add_job_records_table.py` -- Create `job_records` table

The `job_records` table schema (from pattern-stack's `JobRecord` model):

```sql
CREATE TABLE job_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(100) NOT NULL,
    payload JSON NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    result JSON,
    error TEXT
);

CREATE INDEX ix_job_records_status ON job_records (status);
CREATE INDEX ix_job_records_job_type ON job_records (job_type);
CREATE INDEX ix_job_records_priority ON job_records (priority DESC, created_at ASC);
```

**JobDispatcher design:**

```python
# molecules/events/job_dispatcher.py
class JobDispatcher:
    """Bridges app domain Job model to framework JobQueue."""

    def __init__(self):
        self._queue = get_job_queue()

    async def dispatch_develop_job(self, job: Job) -> JobRecord:
        """Enqueue a develop job for async execution."""
        record = await self._queue.enqueue(
            job_type="develop.run",
            payload={"job_id": str(job.id)},
            priority=0,
        )
        # Link app job to framework record
        job.job_record_id = record.id
        return record

    async def dispatch_cascade_job(self, cascade: MergeCascade) -> JobRecord:
        """Enqueue a merge cascade for async execution."""
        return await self._queue.enqueue(
            job_type="cascade.run",
            payload={"cascade_id": str(cascade.id)},
            priority=1,  # Higher priority than develop jobs
        )

    async def dispatch_restack_job(
        self, stack_id: UUID, repo_url: str, trunk: str, branches: list[dict]
    ) -> JobRecord:
        """Enqueue a remote restack for async execution."""
        return await self._queue.enqueue(
            job_type="restack.run",
            payload={
                "stack_id": str(stack_id),
                "repo_url": repo_url,
                "trunk": trunk,
                "branches": branches,
            },
            priority=1,
        )
```

**Job handler functions:**

```python
# molecules/events/job_handlers.py

async def handle_develop_job(job: JobRecord) -> None:
    """Handler for develop.run jobs."""
    job_id = UUID(job.payload["job_id"])
    # Load app Job, run DevelopWorkflow, update state
    pass

async def handle_cascade_job(job: JobRecord) -> None:
    """Handler for cascade.run jobs."""
    cascade_id = UUID(job.payload["cascade_id"])
    # Load MergeCascade, execute steps, update state
    pass

async def handle_restack_job(job: JobRecord) -> None:
    """Handler for restack.run jobs."""
    # Use RemoteRestackService, emit events on completion
    pass
```

**Startup wiring:**

```python
# In configure_subsystems()
configure_jobs(
    JobConfig(backend="database", max_concurrent=settings.JOB_MAX_CONCURRENT),
    session_factory=session_factory,
)
queue = get_job_queue()
queue.register_handler("develop.run", handle_develop_job)
queue.register_handler("cascade.run", handle_cascade_job)
queue.register_handler("restack.run", handle_restack_job)

# Start worker
worker = Worker(queue, max_concurrent=settings.JOB_MAX_CONCURRENT)
await worker.start()
```

### Phase 6: Integration Tests

**Files to create:**

- `app/backend/__tests__/molecules/test_event_middleware.py`
- `app/backend/__tests__/molecules/test_event_handlers.py`
- `app/backend/__tests__/molecules/test_job_dispatcher.py`
- `app/backend/__tests__/organisms/test_events_router.py`

**Testing strategy:**

- Use `reset_event_store()`, `reset_jobs()`, `reset_broadcast()` in fixtures for isolation
- EventStore tests: emit events, query them back, verify persistence
- EventBus tests: subscribe handlers, emit events, verify handler invocation
- Broadcast tests: use MemoryBroadcast, subscribe, verify delivery
- SSE endpoint tests: use httpx async client to read SSE stream
- Job tests: use InMemoryBackend for fast test execution, register handlers, verify dispatch and completion

**Fixture additions to conftest.py:**

```python
from pattern_stack.atoms.shared.events import reset_event_store, reset_event_system
from pattern_stack.atoms.broadcast import reset_broadcast
from pattern_stack.atoms.jobs import reset_jobs

@pytest.fixture(autouse=True)
def reset_subsystem_singletons():
    yield
    reset_event_store()
    reset_event_system()
    reset_broadcast()
    reset_jobs()
```

## File Tree

### New Files

```
app/backend/src/molecules/events/
    __init__.py                     # Package exports
    startup.py                      # configure_subsystems() function
    middleware.py                    # EventMiddleware class
    types.py                        # Event type string constants
    registry.py                     # register_event_handlers()
    handlers.py                     # EventBus handler functions
    job_dispatcher.py               # JobDispatcher class
    job_handlers.py                 # Job execution handler functions

app/backend/src/organisms/api/routers/
    events.py                       # SSE stream + history endpoints

app/backend/alembic/versions/
    XXXX_add_job_records_table.py   # job_records table migration

app/backend/__tests__/molecules/
    test_event_middleware.py         # EventMiddleware unit tests
    test_event_handlers.py          # Handler tests
    test_job_dispatcher.py          # JobDispatcher tests

app/backend/__tests__/organisms/
    __init__.py                     # Package init (if not exists)
    test_events_router.py           # SSE endpoint tests
```

### Modified Files

```
app/backend/src/config/settings.py              # Add EVENT_BACKEND, BROADCAST_BACKEND, JOB_MAX_CONCURRENT
app/backend/src/organisms/api/app.py             # Call configure_subsystems() in lifespan, register events router
app/backend/src/organisms/api/dependencies.py    # Add EventMiddleware, JobDispatcher dependencies
app/backend/src/molecules/entities/stack_entity.py       # Add EventMiddleware calls
app/backend/src/molecules/entities/conversation_entity.py # Add EventMiddleware calls
app/backend/src/molecules/apis/stack_api.py      # Emit business events (synced, merged)
app/backend/__tests__/conftest.py                # Add subsystem reset fixtures
```

## Implementation Order

1. **Phase 1: Subsystem initialization** (no dependencies)
   - Add settings
   - Create `molecules/events/startup.py`
   - Wire into lifespan
   - Create `job_records` migration
   - Verify: app starts with all subsystems initialized

2. **Phase 2: EventMiddleware** (depends on Phase 1)
   - Create middleware class
   - Create event type constants
   - Add to StackEntity and ConversationEntity
   - Verify: state transitions produce events in `system_events` table

3. **Phase 3: EventBus handlers** (depends on Phase 2)
   - Create handler registry
   - Implement broadcast bridge handler
   - Wire into startup
   - Verify: events flow from model -> EventStore -> EventBus -> handlers

4. **Phase 4: SSE endpoint** (depends on Phase 1, can parallel Phase 2-3)
   - Create events router with SSE stream
   - Add history query endpoint
   - Register router
   - Verify: browser can connect to SSE and see events

5. **Phase 5: Jobs wiring** (depends on Phase 1)
   - Create JobDispatcher
   - Create job handler stubs
   - Register handlers and start Worker
   - Verify: enqueued jobs are picked up and executed

6. **Phase 6: Tests** (depends on all above)
   - Add subsystem reset fixtures
   - Write unit tests for middleware, handlers, dispatcher
   - Write integration tests for SSE endpoint

## Key Design Decisions

### Why EventMiddleware in the Molecule Layer (Not Automatic in BaseService)

The framework's `emit_state_transitions = True` flag on models is a declaration of intent, but the actual emission must happen in context -- the molecule layer knows the business context (which user triggered it, what related entities are affected). Automatic emission from BaseService would lose this context. The middleware pattern lets entities emit rich events with full metadata.

### Why Keep the App's Job Model Alongside Framework JobRecord

The app's `Job` model captures domain-specific state (phases, gates, artifacts, issue context) that the framework's `JobRecord` does not model. `JobRecord` is a queue management primitive -- it tracks retries, priority, and worker assignment. The two models serve different purposes and are linked via `Job.job_record_id`.

### Why Memory Broadcast Backend (Not Redis) Initially

The app currently runs as a single process. Memory broadcast is zero-config and sufficient. The `BROADCAST_BACKEND` setting makes it trivial to switch to Redis when multi-process deployment is needed.

### Why Not WebSocket for Client Push

SSE (Server-Sent Events) is simpler, works over standard HTTP, and is sufficient for server-to-client push. The event stream is one-directional (server pushes state updates to UI). WebSocket would add complexity for no benefit since the client never pushes events back through this channel.

### Why a Broadcast Bridge Handler Instead of Direct Broadcast in EventMiddleware

Keeping broadcast as an EventBus handler (rather than calling `broadcast.broadcast()` directly in the middleware) provides a clean separation. The middleware emits to EventSystem which persists and publishes. The bridge handler on the bus forwards to broadcast. This means:
- Handlers can filter/transform before broadcasting
- Testing is simpler (mock the bus, not broadcast)
- Additional handlers can subscribe without modifying middleware

## Open Questions

1. **Channel granularity for SSE**: Should clients subscribe per-stack (e.g., `stack:{id}`) or per-entity-type (e.g., `stack`, `branch`)? Per-type is simpler to start; per-entity can be added later using Broadcast channel naming.

2. **Event retention policy**: The `system_events` table will grow. Should we set `expires_at` on events and run `cleanup_expired_events()` periodically? The `HistoryCapability` on Job and AgentRun already declares `retention="90d"`.

3. **Worker lifecycle**: Should the Worker run in-process (started in lifespan, stopped on shutdown) or as a separate process? In-process is simpler for MVP; separate process scales better.

4. **Backpressure on SSE**: If a client falls behind, the async queue will grow. Should we add a max queue size and drop old events for slow clients?
