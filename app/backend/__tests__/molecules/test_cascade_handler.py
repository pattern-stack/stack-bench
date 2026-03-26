"""Tests for the cascade handler -- reactive handler for PR merge events."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from molecules.events.handlers.cascade_handler import on_pull_request_merged


def _make_event(payload: dict) -> MagicMock:
    """Create a mock Event with .data containing the given payload."""
    event = MagicMock()
    event.data = {
        "entity_type": "pull_request",
        "entity_id": str(uuid4()),
        "payload": payload,
        "source": "system",
        "correlation_id": None,
        "timestamp": "2026-03-26T00:00:00+00:00",
        "event_id": str(uuid4()),
    }
    return event


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatches_cascade_job_when_stack_id_present() -> None:
    """When a PR merge event includes a stack_id, a cascade job is dispatched."""
    mock_record = MagicMock()
    mock_record.id = uuid4()

    event = _make_event({"stack_id": str(uuid4()), "branch_id": str(uuid4())})

    with (
        patch(
            "molecules.events.handlers.cascade_handler.dispatch_job",
            new_callable=AsyncMock,
            return_value=mock_record,
        ) as mock_dispatch,
        patch(
            "molecules.events.handlers.cascade_handler.publish",
            new_callable=AsyncMock,
        ),
    ):
        await on_pull_request_merged(event)

        mock_dispatch.assert_awaited_once()
        call_args = mock_dispatch.call_args
        assert call_args[0][0] == "merge.cascade"
        assert "stack_id" in call_args[0][1]
        assert call_args[1]["priority"] == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skips_when_no_stack_id() -> None:
    """When a PR merge event has no stack_id, no cascade job is dispatched."""
    event = _make_event({"branch_id": str(uuid4())})

    with (
        patch(
            "molecules.events.handlers.cascade_handler.dispatch_job",
            new_callable=AsyncMock,
        ) as mock_dispatch,
        patch(
            "molecules.events.handlers.cascade_handler.publish",
            new_callable=AsyncMock,
        ) as mock_publish,
    ):
        await on_pull_request_merged(event)

        mock_dispatch.assert_not_awaited()
        mock_publish.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publishes_cascade_started_event() -> None:
    """After dispatching the job, a MERGE_CASCADE_STARTED event is published."""
    mock_record = MagicMock()
    mock_record.id = uuid4()
    stack_id = str(uuid4())

    event = _make_event({"stack_id": stack_id, "branch_id": str(uuid4())})

    with (
        patch(
            "molecules.events.handlers.cascade_handler.dispatch_job",
            new_callable=AsyncMock,
            return_value=mock_record,
        ),
        patch(
            "molecules.events.handlers.cascade_handler.publish",
            new_callable=AsyncMock,
        ) as mock_publish,
    ):
        await on_pull_request_merged(event)

        mock_publish.assert_awaited_once()
        domain_event = mock_publish.call_args[0][0]
        assert domain_event.topic == "merge_cascade.started"
        assert domain_event.entity_type == "stack"
        assert domain_event.payload["stack_id"] == stack_id
        assert domain_event.payload["cascade_id"] == str(mock_record.id)
