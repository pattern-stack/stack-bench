"""Wire event handlers to the EventBus at application startup."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pattern_stack.atoms.broadcast import get_broadcast, reset_broadcast
from pattern_stack.atoms.jobs import JobConfig, configure_jobs, get_job_queue, reset_jobs
from pattern_stack.atoms.shared.events import get_event_bus, get_event_store, reset_event_store

if TYPE_CHECKING:
    from collections.abc import Callable

    from config.settings import AppSettings

from . import topics
from .handlers.broadcast_bridge import handle_for_broadcast
from .handlers.cascade_handler import on_pull_request_merged
from .job_handlers import register_job_handlers

logger = logging.getLogger(__name__)

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
    topics.STACK_PUSHED,
    topics.STACK_SUBMITTED,
    topics.STACK_MARKED_READY,
]


@dataclass
class SubsystemRefs:
    """References to configured subsystems for lifecycle management."""

    event_bus: Any = None
    event_store: Any = None
    broadcast: Any = None
    job_queue: Any = None
    extras: dict[str, Any] = field(default_factory=dict)


def configure_subsystems(
    settings: AppSettings,
    session_factory: Callable[..., Any] | None = None,
) -> SubsystemRefs:
    """Initialize all infrastructure subsystems based on settings.

    Call this at application startup, before setup_event_handlers().

    Args:
        settings: Application settings with subsystem configuration.
        session_factory: Async session factory for database-backed subsystems.

    Returns:
        SubsystemRefs with references to the configured subsystems.
    """
    refs = SubsystemRefs()

    # 1. Events — bus and store use singletons, no explicit configure needed
    refs.event_bus = get_event_bus()
    refs.event_store = get_event_store()
    logger.info("Event subsystem initialized (backend=%s)", settings.EVENT_BACKEND)

    # 2. Broadcast — singleton, no configure function
    refs.broadcast = get_broadcast()
    logger.info("Broadcast subsystem initialized (backend=%s)", settings.BROADCAST_BACKEND)

    # 3. Jobs — requires explicit configuration
    job_config = JobConfig(
        backend=settings.JOB_BACKEND,
        max_concurrent=settings.JOB_MAX_CONCURRENT,
        poll_interval=settings.JOB_POLL_INTERVAL,
    )
    configure_jobs(job_config, session_factory=session_factory)
    refs.job_queue = get_job_queue()
    logger.info(
        "Jobs subsystem initialized (backend=%s, max_concurrent=%d)",
        settings.JOB_BACKEND,
        settings.JOB_MAX_CONCURRENT,
    )

    # 4. Job handlers — register after queue is configured
    register_job_handlers(session_factory=session_factory)
    logger.info("Job handlers registered")

    return refs


def teardown_subsystems() -> None:
    """Reset all subsystem singletons. Called on shutdown."""
    reset_jobs()
    reset_broadcast()
    reset_event_store()
    logger.info("All subsystems torn down")


def setup_event_handlers() -> None:
    """Register all event handlers with the EventBus."""
    bus = get_event_bus()

    # Broadcast bridge for all topics
    for topic in ALL_TOPICS:
        bus.subscribe(topic, handle_for_broadcast)

    # Reactive handlers
    bus.subscribe(topics.PULL_REQUEST_MERGED, on_pull_request_merged)


def teardown_event_handlers() -> None:
    """Clear all EventBus handlers. Called on shutdown."""
    bus = get_event_bus()
    bus.clear()
