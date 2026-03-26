"""Tests for the job dispatcher bridge."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_job_enqueues_on_queue() -> None:
    """dispatch_job calls queue.enqueue with correct args."""
    mock_queue = MagicMock()
    mock_record = MagicMock()
    mock_record.id = uuid4()
    mock_queue.enqueue = AsyncMock(return_value=mock_record)

    with patch("molecules.events.job_dispatcher.get_job_queue", return_value=mock_queue):
        from molecules.events.job_dispatcher import dispatch_job

        result = await dispatch_job("sync.stack", {"stack_id": "abc"}, priority=5)

        mock_queue.enqueue.assert_called_once_with("sync.stack", {"stack_id": "abc"}, priority=5)
        assert result is mock_record


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_job_default_priority() -> None:
    """dispatch_job defaults priority to 0."""
    mock_queue = MagicMock()
    mock_record = MagicMock()
    mock_queue.enqueue = AsyncMock(return_value=mock_record)

    with patch("molecules.events.job_dispatcher.get_job_queue", return_value=mock_queue):
        from molecules.events.job_dispatcher import dispatch_job

        await dispatch_job("sync.stack", {"stack_id": "abc"})

        mock_queue.enqueue.assert_called_once_with("sync.stack", {"stack_id": "abc"}, priority=0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_status_returns_formatted_dict() -> None:
    """get_job_status returns a formatted status dict from the queue record."""
    job_id = uuid4()
    mock_record = MagicMock()
    mock_record.id = job_id
    mock_record.job_type = "sync.stack"
    mock_record.status = "running"
    mock_record.payload = {"stack_id": "abc"}
    mock_record.result = None
    mock_record.error = None

    mock_queue = MagicMock()
    mock_queue.get_job = AsyncMock(return_value=mock_record)

    with patch("molecules.events.job_dispatcher.get_job_queue", return_value=mock_queue):
        from molecules.events.job_dispatcher import get_job_status

        result = await get_job_status(job_id)

        assert result is not None
        assert result["id"] == str(job_id)
        assert result["job_type"] == "sync.stack"
        assert result["status"] == "running"
        assert result["payload"] == {"stack_id": "abc"}
        assert result["result"] is None
        assert result["error"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_status_returns_none_when_not_found() -> None:
    """get_job_status returns None when job doesn't exist."""
    mock_queue = MagicMock()
    mock_queue.get_job = AsyncMock(return_value=None)

    with patch("molecules.events.job_dispatcher.get_job_queue", return_value=mock_queue):
        from molecules.events.job_dispatcher import get_job_status

        result = await get_job_status(uuid4())

        assert result is None
