"""Wire event handlers to the EventBus at application startup."""

from __future__ import annotations

from pattern_stack.atoms.shared.events import get_event_bus

from . import topics
from .handlers.broadcast_bridge import handle_for_broadcast

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
