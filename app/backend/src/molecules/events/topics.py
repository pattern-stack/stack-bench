"""Event topics and domain event envelope for the PubSub system.

Topic constants follow {entity}.{action} naming. DomainEvent is the canonical
envelope shared by all producers. DomainBusEvent adapts it to pattern-stack's
abstract Event class for use on the EventBus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pattern_stack.atoms.shared.events import Event

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

# --- Stack workflow operations ---
STACK_PUSHED = "stack.pushed"
STACK_SUBMITTED = "stack.submitted"
STACK_MARKED_READY = "stack.marked_ready"


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


@dataclass(frozen=True)
class DomainBusEvent(Event):
    """Concrete EventBus event wrapping a DomainEvent.

    Since Event is a frozen dataclass, DomainBusEvent stores the domain
    event's data as frozen fields rather than using a mutable reference.
    """

    _topic: str = ""
    _entity_type: str = ""
    _entity_id: str = ""
    _payload: dict[str, Any] = field(default_factory=dict)
    _source: str = "system"
    _correlation_id: str | None = None

    @classmethod
    def from_domain_event(cls, domain_event: DomainEvent) -> DomainBusEvent:
        """Create a DomainBusEvent from a DomainEvent."""
        return cls(
            event_id=domain_event.event_id,
            timestamp=domain_event.timestamp,
            _topic=domain_event.topic,
            _entity_type=domain_event.entity_type,
            _entity_id=str(domain_event.entity_id),
            _payload=domain_event.payload,
            _source=domain_event.source,
            _correlation_id=domain_event.correlation_id,
        )

    @property
    def event_type(self) -> str:
        return self._topic

    @property
    def data(self) -> dict[str, Any]:
        return {
            "entity_type": self._entity_type,
            "entity_id": self._entity_id,
            "payload": self._payload,
            "source": self._source,
            "correlation_id": self._correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
        }
