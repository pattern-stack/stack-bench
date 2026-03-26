"""Tests for job handlers and registration."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.unit
def test_register_job_handlers_registers_all_types() -> None:
    """register_job_handlers registers handlers for all 3 job types."""
    mock_queue = MagicMock()

    with patch("molecules.events.job_handlers.get_job_queue", return_value=mock_queue):
        from molecules.events.job_handlers import (
            JOB_TYPE_MERGE_CASCADE,
            JOB_TYPE_RESTACK,
            JOB_TYPE_SYNC_STACK,
            register_job_handlers,
        )

        register_job_handlers()

        assert mock_queue.register_handler.call_count == 3

        registered_types = {c[0][0] for c in mock_queue.register_handler.call_args_list}
        assert registered_types == {
            JOB_TYPE_SYNC_STACK,
            JOB_TYPE_MERGE_CASCADE,
            JOB_TYPE_RESTACK,
        }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_sync_stack_completes() -> None:
    """handle_sync_stack runs without error."""
    from molecules.events.job_handlers import handle_sync_stack

    record = MagicMock()
    record.id = uuid4()

    # Should not raise
    await handle_sync_stack(record)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_merge_cascade_completes() -> None:
    """handle_merge_cascade runs without error."""
    from molecules.events.job_handlers import handle_merge_cascade

    record = MagicMock()
    record.id = uuid4()

    await handle_merge_cascade(record)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_restack_completes() -> None:
    """handle_restack runs without error."""
    from molecules.events.job_handlers import handle_restack

    record = MagicMock()
    record.id = uuid4()

    await handle_restack(record)


@pytest.mark.unit
def test_register_job_handlers_passes_correct_handler_functions() -> None:
    """Each job type is registered with the correct handler function."""
    mock_queue = MagicMock()

    with patch("molecules.events.job_handlers.get_job_queue", return_value=mock_queue):
        from molecules.events.job_handlers import (
            JOB_TYPE_MERGE_CASCADE,
            JOB_TYPE_RESTACK,
            JOB_TYPE_SYNC_STACK,
            handle_merge_cascade,
            handle_restack,
            handle_sync_stack,
            register_job_handlers,
        )

        register_job_handlers()

        # Build a map of registered type -> handler
        registered = {c[0][0]: c[0][1] for c in mock_queue.register_handler.call_args_list}

        assert registered[JOB_TYPE_SYNC_STACK] is handle_sync_stack
        assert registered[JOB_TYPE_MERGE_CASCADE] is handle_merge_cascade
        assert registered[JOB_TYPE_RESTACK] is handle_restack
