"""Reactive handler: when a PR is merged, check if downstream PRs need cascading."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from molecules.events import MERGE_CASCADE_STARTED, DomainEvent, publish
from molecules.events.job_dispatcher import dispatch_job
from molecules.events.job_handlers import JOB_TYPE_MERGE_CASCADE

if TYPE_CHECKING:
    from pattern_stack.atoms.shared.events import Event

logger = logging.getLogger(__name__)


async def on_pull_request_merged(event: Event) -> None:
    """React to a PR merge by potentially starting a merge cascade.

    When a PR is merged, downstream branches in the stack may need to be
    rebased and merged as well. This handler dispatches a merge cascade job
    if there are downstream PRs.
    """
    data: dict[str, Any] = cast("Any", event).data
    payload = data.get("payload", {})
    stack_id = payload.get("stack_id")
    branch_id = payload.get("branch_id")

    if not stack_id:
        logger.debug("PR merged event without stack_id, skipping cascade check")
        return

    logger.info(
        "PR merged in stack %s (branch %s), dispatching cascade check",
        stack_id,
        branch_id,
    )

    # Dispatch a cascade job -- the job handler will determine if
    # there are actually downstream PRs to merge
    record = await dispatch_job(
        JOB_TYPE_MERGE_CASCADE,
        {"stack_id": stack_id, "trigger_branch_id": branch_id},
        priority=10,  # High priority
    )

    # Publish cascade started event
    await publish(
        DomainEvent(
            topic=MERGE_CASCADE_STARTED,
            entity_type="stack",
            entity_id=UUID(stack_id),
            source="cascade",
            payload={
                "cascade_id": str(record.id),
                "stack_id": stack_id,
            },
        )
    )
