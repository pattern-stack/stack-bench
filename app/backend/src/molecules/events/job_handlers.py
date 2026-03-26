"""Job handlers for async operations.

Each handler receives a JobRecord and performs the work. Handlers are
registered with the JobQueue at startup via register_job_handlers().
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pattern_stack.atoms.jobs import get_job_queue

if TYPE_CHECKING:
    from pattern_stack.atoms.jobs import JobRecord

logger = logging.getLogger(__name__)

# Job type constants
JOB_TYPE_SYNC_STACK = "sync.stack"
JOB_TYPE_MERGE_CASCADE = "merge.cascade"
JOB_TYPE_RESTACK = "restack.run"


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


def register_job_handlers() -> None:
    """Register all job handlers with the JobQueue."""
    queue = get_job_queue()
    queue.register_handler(JOB_TYPE_SYNC_STACK, handle_sync_stack)
    queue.register_handler(JOB_TYPE_MERGE_CASCADE, handle_merge_cascade)
    queue.register_handler(JOB_TYPE_RESTACK, handle_restack)
