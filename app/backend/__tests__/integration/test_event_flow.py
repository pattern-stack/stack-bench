"""Integration tests for the event subsystem.

These tests use real (memory-backed) subsystem instances rather than mocks,
verifying the full flow from event publishing through handler execution.
"""

import asyncio
from uuid import uuid4

import pytest

from molecules.events import (
    BRANCH_SYNCED,
    MERGE_CASCADE_STARTED,
    PULL_REQUEST_MERGED,
    SYNC_STACK_COMPLETED,
    DomainEvent,
    publish,
)
from molecules.events.job_dispatcher import dispatch_job, get_job_status
from molecules.events.job_handlers import JOB_TYPE_MERGE_CASCADE
from molecules.events.setup import (
    configure_subsystems,
    setup_event_handlers,
    teardown_event_handlers,
    teardown_subsystems,
)
from pattern_stack.atoms.broadcast import get_broadcast
from pattern_stack.atoms.jobs import get_job_queue
from pattern_stack.atoms.shared.events import (
    EventFilters,
    get_event_bus,
    get_event_store,
)


@pytest.fixture(autouse=True)
async def _setup_subsystems(clean_event_subsystems):
    """Configure subsystems with memory backends for integration tests.

    Forces the EventStore to use memory backend (not database) via
    EventStoreConfig.configure_for_testing(), then wires up handlers.
    """
    from pattern_stack.atoms.shared.events import EventStoreConfig

    # Force memory-backed EventStore before configure_subsystems runs
    EventStoreConfig.configure_for_testing(publish_to_bus=False)

    from config.settings import get_settings

    settings = get_settings()
    configure_subsystems(settings, session_factory=None)
    setup_event_handlers()
    yield
    teardown_event_handlers()
    teardown_subsystems()


# ---------------------------------------------------------------------------
# Publish flow: publish() -> EventBus -> EventStore
# ---------------------------------------------------------------------------


class TestEventPublishFlow:
    """Verify events flow from publish() through EventBus to EventStore."""

    @pytest.mark.integration
    async def test_publish_records_in_event_store(self):
        """Publishing a DomainEvent should record it in the EventStore."""
        entity_id = uuid4()
        event = DomainEvent(
            topic=BRANCH_SYNCED,
            entity_type="branch",
            entity_id=entity_id,
            source="sync",
            payload={"stack_id": str(uuid4()), "action": "created"},
        )
        await publish(event)

        store = get_event_store()
        events = await store.query(EventFilters(entity_type="branch", limit=10))

        assert len(events) >= 1
        found = any(e.entity_id == entity_id for e in events)
        assert found, "Published event should be found in EventStore"

    @pytest.mark.integration
    async def test_publish_triggers_broadcast_bridge(self):
        """Publishing should trigger the broadcast bridge and deliver to subscribers."""
        broadcast = get_broadcast()
        received: list[dict] = []

        async def on_event(event_type: str, payload: dict) -> None:
            received.append({"event_type": event_type, "payload": payload})

        await broadcast.subscribe("global", on_event)

        await publish(
            DomainEvent(
                topic=SYNC_STACK_COMPLETED,
                entity_type="stack",
                entity_id=uuid4(),
                source="sync",
                payload={"synced_count": 5},
            )
        )

        # Give async handlers time to execute
        await asyncio.sleep(0.1)

        assert len(received) >= 1
        assert received[0]["event_type"] == SYNC_STACK_COMPLETED

    @pytest.mark.integration
    async def test_publish_routes_to_stack_channel(self):
        """Events with stack_id in payload should be routed to a stack-specific channel."""
        broadcast = get_broadcast()
        stack_id = str(uuid4())
        stack_received: list[dict] = []

        async def on_stack_event(event_type: str, payload: dict) -> None:
            stack_received.append({"event_type": event_type, "payload": payload})

        await broadcast.subscribe(f"stack:{stack_id}", on_stack_event)

        await publish(
            DomainEvent(
                topic=BRANCH_SYNCED,
                entity_type="branch",
                entity_id=uuid4(),
                source="sync",
                payload={"stack_id": stack_id, "action": "updated"},
            )
        )

        await asyncio.sleep(0.1)

        assert len(stack_received) >= 1
        assert stack_received[0]["event_type"] == BRANCH_SYNCED

    @pytest.mark.integration
    async def test_multiple_events_accumulate_in_store(self):
        """Multiple published events should all be queryable from EventStore."""
        store = get_event_store()

        for i in range(5):
            await publish(
                DomainEvent(
                    topic=BRANCH_SYNCED,
                    entity_type="branch",
                    entity_id=uuid4(),
                    source="sync",
                    payload={"index": i},
                )
            )

        events = await store.query(
            EventFilters(entity_type="branch", event_type=BRANCH_SYNCED, limit=20)
        )
        assert len(events) >= 5


# ---------------------------------------------------------------------------
# Cascade handler flow: PULL_REQUEST_MERGED -> cascade_handler -> job dispatch
# ---------------------------------------------------------------------------


class TestCascadeHandlerFlow:
    """Verify the cascade handler fires when a PR merged event is published."""

    @pytest.mark.integration
    async def test_pr_merged_dispatches_cascade_job(self):
        """PULL_REQUEST_MERGED should trigger cascade handler and dispatch a job."""
        queue = get_job_queue()
        stack_id = str(uuid4())

        await publish(
            DomainEvent(
                topic=PULL_REQUEST_MERGED,
                entity_type="pull_request",
                entity_id=uuid4(),
                source="user_action",
                payload={
                    "stack_id": stack_id,
                    "branch_id": str(uuid4()),
                    "external_id": 42,
                },
            )
        )

        # Let async handlers (bus -> cascade handler -> dispatch_job) complete
        await asyncio.sleep(0.2)

        # The cascade handler should have dispatched a merge.cascade job
        job = await queue.dequeue()
        assert job is not None, "A merge.cascade job should have been enqueued"
        assert job.job_type == JOB_TYPE_MERGE_CASCADE
        assert job.payload["stack_id"] == stack_id

    @pytest.mark.integration
    async def test_pr_merged_publishes_cascade_started_event(self):
        """Cascade handler should also publish a MERGE_CASCADE_STARTED event."""
        store = get_event_store()
        stack_id = str(uuid4())

        await publish(
            DomainEvent(
                topic=PULL_REQUEST_MERGED,
                entity_type="pull_request",
                entity_id=uuid4(),
                source="user_action",
                payload={
                    "stack_id": stack_id,
                    "branch_id": str(uuid4()),
                    "external_id": 99,
                },
            )
        )

        await asyncio.sleep(0.2)

        events = await store.query(
            EventFilters(event_type=MERGE_CASCADE_STARTED, limit=10)
        )
        assert len(events) >= 1
        # The cascade event should reference the same stack
        cascade_event = events[0]
        metadata = getattr(cascade_event, "event_metadata", {}) or getattr(
            cascade_event, "metadata", {}
        )
        assert metadata.get("stack_id") == stack_id


# ---------------------------------------------------------------------------
# Job dispatcher flow: dispatch_job -> enqueue -> get_job_status
# ---------------------------------------------------------------------------


class TestJobDispatcherFlow:
    """Verify job dispatch and status retrieval."""

    @pytest.mark.integration
    async def test_dispatch_and_get_status(self):
        """dispatch_job should enqueue and get_job_status should retrieve it."""
        record = await dispatch_job("test.job", {"key": "value"}, priority=5)
        assert record is not None
        assert record.id is not None

        status = await get_job_status(record.id)
        assert status is not None
        assert status["job_type"] == "test.job"
        assert status["status"] in ("pending", "queued")

    @pytest.mark.integration
    async def test_dispatch_preserves_payload(self):
        """Dispatched job should retain its payload when retrieved."""
        payload = {"stack_id": str(uuid4()), "action": "rebase"}
        record = await dispatch_job("restack.run", payload, priority=1)

        status = await get_job_status(record.id)
        assert status is not None
        assert status["payload"]["stack_id"] == payload["stack_id"]
        assert status["payload"]["action"] == payload["action"]

    @pytest.mark.integration
    async def test_dispatch_multiple_jobs_dequeue_by_priority(self):
        """Higher priority jobs should be dequeued first."""
        queue = get_job_queue()

        low = await dispatch_job("low.priority", {"p": "low"}, priority=1)
        high = await dispatch_job("high.priority", {"p": "high"}, priority=10)

        first = await queue.dequeue()
        assert first is not None
        assert first.id == high.id, "Higher priority job should be dequeued first"

        second = await queue.dequeue()
        assert second is not None
        assert second.id == low.id


# ---------------------------------------------------------------------------
# EventBus handler registration
# ---------------------------------------------------------------------------


class TestEventBusHandlerRegistration:
    """Verify that setup_event_handlers registers the expected handlers."""

    @pytest.mark.integration
    async def test_all_topics_have_broadcast_handler(self):
        """Every domain topic should have at least one handler (the broadcast bridge)."""
        from molecules.events.setup import ALL_TOPICS

        bus = get_event_bus()
        for topic in ALL_TOPICS:
            count = bus.get_handler_count(topic)
            assert count >= 1, f"Topic {topic} should have at least 1 handler, got {count}"

    @pytest.mark.integration
    async def test_pr_merged_has_cascade_handler(self):
        """PULL_REQUEST_MERGED should have 2 handlers: broadcast bridge + cascade."""
        bus = get_event_bus()
        count = bus.get_handler_count(PULL_REQUEST_MERGED)
        assert count >= 2, (
            f"PULL_REQUEST_MERGED should have >= 2 handlers "
            f"(broadcast + cascade), got {count}"
        )
