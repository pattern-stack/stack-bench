"""Job handlers for async operations.

Each handler receives a JobRecord and performs the work. Handlers are
registered with the JobQueue at startup via register_job_handlers().

Also registers EventBus handlers for Job state transitions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, cast

from pattern_stack.atoms.jobs import get_job_queue
from pattern_stack.atoms.shared.events import get_event_bus

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from pattern_stack.atoms.jobs import JobRecord
    from pattern_stack.atoms.shared.events import Event

logger = logging.getLogger(__name__)

# Module-level session factory reference, set during register_job_handlers
_session_factory: Callable[..., Any] | None = None

# Job type constants
JOB_TYPE_SYNC_STACK = "sync.stack"
JOB_TYPE_MERGE_CASCADE = "merge.cascade"
JOB_TYPE_RESTACK = "restack.run"

# Event topic for job state transitions
JOB_STATE_CHANGED = "job.state_changed"


async def handle_sync_stack(record: JobRecord) -> None:
    """Handle async stack sync job."""
    logger.info("Processing sync.stack job %s", record.id)
    # Placeholder -- actual implementation will call StackEntity.sync_stack
    # with the payload data. For now, just log.
    logger.info("sync.stack job %s completed (stub)", record.id)


async def handle_merge_cascade(record: JobRecord) -> None:
    """Handle merge cascade job."""
    logger.info("Processing merge.cascade job %s", record.id)
    # Placeholder -- actual implementation will walk the stack DAG
    logger.info("merge.cascade job %s completed (stub)", record.id)


async def handle_restack(record: JobRecord) -> None:
    """Handle restack job."""
    logger.info("Processing restack.run job %s", record.id)
    # Placeholder -- actual implementation will call git rebase operations
    logger.info("restack.run job %s completed (stub)", record.id)


async def handle_job_state_changed(event: Event) -> None:
    """Handle job state transition events.

    When a job transitions to 'running', trigger agent execution
    on the linked conversation as a background task.

    EventPattern state transitions put phase_from/phase_to in metadata
    (not state_from/state_to). Job "running" maps to StatePhase.ACTIVE.
    """
    notification = cast("Any", event)
    metadata = getattr(notification, "metadata", {})
    phase_to = metadata.get("phase_to", "")

    if phase_to != "active":
        return

    entity_id = getattr(notification, "entity_id", None)
    if not entity_id:
        return

    logger.info("Job %s transitioned to running — triggering conversation execution", entity_id)

    from uuid import UUID as _UUID

    job_id = _UUID(str(entity_id)) if not isinstance(entity_id, _UUID) else entity_id
    asyncio.create_task(_run_job_conversation(job_id))


async def _run_job_conversation(job_id: UUID) -> None:
    """Background task to execute job conversation."""
    if _session_factory is None:
        logger.error("Session factory not set — cannot execute job conversation")
        return
    try:
        async with _session_factory() as db:
            from molecules.runtime.job_execution_bridge import execute_job_conversation

            await execute_job_conversation(db, job_id)
    except Exception:
        logger.exception("Failed to execute conversation for job %s", job_id)


def register_job_handlers(
    session_factory: Callable[..., Any] | None = None,
) -> None:
    """Register all job handlers with the JobQueue and EventBus.

    Args:
        session_factory: Async session factory for DB access in background tasks.
    """
    global _session_factory  # noqa: PLW0603
    if session_factory is not None:
        _session_factory = session_factory

    queue = get_job_queue()
    queue.register_handler(JOB_TYPE_SYNC_STACK, handle_sync_stack)
    queue.register_handler(JOB_TYPE_MERGE_CASCADE, handle_merge_cascade)
    queue.register_handler(JOB_TYPE_RESTACK, handle_restack)

    # Subscribe to job state transitions on the EventBus
    bus = get_event_bus()
    bus.subscribe(JOB_STATE_CHANGED, handle_job_state_changed)
