"""Bridge app Job model to pattern-stack's JobQueue.

When a Job is created in the database, the dispatcher enqueues it on the
framework's JobQueue so the Worker can pick it up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

from pattern_stack.atoms.jobs import get_job_queue

if TYPE_CHECKING:
    from pattern_stack.atoms.jobs import JobRecord


async def dispatch_job(job_type: str, payload: dict[str, Any], priority: int = 0) -> JobRecord:
    """Enqueue a job on the framework's JobQueue.

    Returns the JobRecord which contains the job_id for tracking.
    """
    queue = get_job_queue()
    return await queue.enqueue(job_type, payload, priority=priority)


async def get_job_status(job_id: UUID) -> dict[str, Any] | None:
    """Get the status of a job from the queue."""
    queue = get_job_queue()
    record = await queue.get_job(job_id)
    if record is None:
        return None
    return {
        "id": str(record.id),
        "job_type": record.job_type,
        "status": record.status,
        "payload": record.payload,
        "result": record.result,
        "error": record.error,
    }
