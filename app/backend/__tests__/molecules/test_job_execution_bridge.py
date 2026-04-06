"""Tests for Job→Conversation execution bridge."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.unit
async def test_execute_job_conversation_finds_linked_conversation() -> None:
    """Bridge should find conversation linked to the job and run the runner."""
    from molecules.runtime.job_execution_bridge import execute_job_conversation

    job_id = uuid4()
    conv_id = uuid4()
    db = AsyncMock()

    # Mock context link
    mock_context = MagicMock()
    mock_context.conversation_id = conv_id

    # Mock job
    mock_job = MagicMock()
    mock_job.input_text = "Build the feature"

    mock_conv_svc = AsyncMock()
    mock_conv_svc.get_conversation_for_entity = AsyncMock(return_value=mock_context)

    mock_job_svc = AsyncMock()
    mock_job_svc.get = AsyncMock(return_value=mock_job)

    mock_runner = MagicMock()

    async def mock_send(cid, message, **kwargs):
        yield "event: agent.message.complete\ndata: {}\n\n"

    mock_runner.send = mock_send

    with (
        patch(
            "molecules.runtime.job_execution_bridge.ConversationService",
            return_value=mock_conv_svc,
        ),
        patch(
            "molecules.runtime.job_execution_bridge.JobService",
            return_value=mock_job_svc,
        ),
        patch(
            "molecules.runtime.job_execution_bridge.ConversationRunner",
            return_value=mock_runner,
        ),
    ):
        await execute_job_conversation(db, job_id)

    # Verify conversation service was queried for the job's linked conversation
    mock_conv_svc.get_conversation_for_entity.assert_awaited_once_with(
        db,
        entity_type="job",
        entity_id=job_id,
        role="execution",
    )


@pytest.mark.unit
async def test_execute_job_conversation_uses_job_input_text() -> None:
    """Bridge should use job.input_text as the message prompt."""
    from molecules.runtime.job_execution_bridge import execute_job_conversation

    job_id = uuid4()
    conv_id = uuid4()
    db = AsyncMock()

    mock_context = MagicMock()
    mock_context.conversation_id = conv_id

    mock_job = MagicMock()
    mock_job.input_text = "Implement OAuth flow"
    mock_job.reference_number = "JOB-001"

    mock_conv_svc = AsyncMock()
    mock_conv_svc.get_conversation_for_entity = AsyncMock(return_value=mock_context)

    mock_job_svc = AsyncMock()
    mock_job_svc.get = AsyncMock(return_value=mock_job)

    sent_messages: list[str] = []

    mock_runner = MagicMock()

    async def mock_send(cid, message, **kwargs):
        sent_messages.append(message)
        yield "event: done\ndata: {}\n\n"

    mock_runner.send = mock_send

    with (
        patch(
            "molecules.runtime.job_execution_bridge.ConversationService",
            return_value=mock_conv_svc,
        ),
        patch(
            "molecules.runtime.job_execution_bridge.JobService",
            return_value=mock_job_svc,
        ),
        patch(
            "molecules.runtime.job_execution_bridge.ConversationRunner",
            return_value=mock_runner,
        ),
    ):
        await execute_job_conversation(db, job_id)

    assert sent_messages == ["Implement OAuth flow"]


@pytest.mark.unit
async def test_execute_job_conversation_no_linked_conversation() -> None:
    """Bridge should return early if no conversation is linked to the job."""
    from molecules.runtime.job_execution_bridge import execute_job_conversation

    job_id = uuid4()
    db = AsyncMock()

    mock_conv_svc = AsyncMock()
    mock_conv_svc.get_conversation_for_entity = AsyncMock(return_value=None)

    mock_runner = MagicMock()
    mock_runner.send = AsyncMock()

    with (
        patch(
            "molecules.runtime.job_execution_bridge.ConversationService",
            return_value=mock_conv_svc,
        ),
        patch(
            "molecules.runtime.job_execution_bridge.ConversationRunner",
            return_value=mock_runner,
        ),
    ):
        # Should not raise
        await execute_job_conversation(db, job_id)

    # Runner.send should NOT have been called
    mock_runner.send.assert_not_called()


@pytest.mark.unit
async def test_execute_job_conversation_fallback_prompt() -> None:
    """Bridge should use a fallback prompt when job.input_text is empty."""
    from molecules.runtime.job_execution_bridge import execute_job_conversation

    job_id = uuid4()
    conv_id = uuid4()
    db = AsyncMock()

    mock_context = MagicMock()
    mock_context.conversation_id = conv_id

    mock_job = MagicMock()
    mock_job.input_text = None
    mock_job.reference_number = "JOB-042"

    mock_conv_svc = AsyncMock()
    mock_conv_svc.get_conversation_for_entity = AsyncMock(return_value=mock_context)

    mock_job_svc = AsyncMock()
    mock_job_svc.get = AsyncMock(return_value=mock_job)

    sent_messages: list[str] = []

    mock_runner = MagicMock()

    async def mock_send(cid, message, **kwargs):
        sent_messages.append(message)
        yield "event: done\ndata: {}\n\n"

    mock_runner.send = mock_send

    with (
        patch(
            "molecules.runtime.job_execution_bridge.ConversationService",
            return_value=mock_conv_svc,
        ),
        patch(
            "molecules.runtime.job_execution_bridge.JobService",
            return_value=mock_job_svc,
        ),
        patch(
            "molecules.runtime.job_execution_bridge.ConversationRunner",
            return_value=mock_runner,
        ),
    ):
        await execute_job_conversation(db, job_id)

    assert sent_messages == ["Execute job JOB-042"]
