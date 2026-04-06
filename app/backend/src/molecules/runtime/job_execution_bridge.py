"""Bridge between Job execution and Conversation runner.

When a Job transitions to "running", this module finds the linked
conversation and triggers agent execution with the job's input text.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from features.conversations.service import ConversationService
from features.jobs.service import JobService
from molecules.runtime.conversation_runner import ConversationRunner

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def execute_job_conversation(
    db: AsyncSession,
    job_id: UUID,
) -> None:
    """Find the conversation linked to a job and trigger agent execution."""
    conv_svc = ConversationService()
    context = await conv_svc.get_conversation_for_entity(
        db,
        entity_type="job",
        entity_id=job_id,
        role="execution",
    )
    if context is None:
        logger.warning("No conversation linked to job %s", job_id)
        return

    # Load the job for its input_text
    job_svc = JobService()
    job = await job_svc.get(db, job_id)
    prompt = job.input_text or f"Execute job {job.reference_number}"

    # Run through ConversationRunner (drain the stream — events are broadcast)
    runner = ConversationRunner(db)
    async for _chunk in runner.send(context.conversation_id, prompt):
        pass
