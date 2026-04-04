from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from molecules.apis.stack_api import StackAPI
from molecules.entities.stack_entity import StackEntity


@pytest.mark.unit
def test_stack_api_init() -> None:
    """Verify StackAPI composes StackEntity."""
    db = AsyncMock()
    api = StackAPI(db)
    assert hasattr(api, "entity")


@pytest.mark.unit
def test_stack_api_has_entity() -> None:
    """Verify entity is correct type."""
    db = AsyncMock()
    api = StackAPI(db)
    assert isinstance(api.entity, StackEntity)


# ---------------------------------------------------------------------------
# Workflow facade methods
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_push_stack_publishes_event() -> None:
    """Push should publish STACK_PUSHED event."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github)
    stack_id = uuid4()

    api.entity.push_stack = AsyncMock(
        return_value={
            "branches": [],
            "synced_count": 0,
            "created_count": 1,
        }
    )

    with patch("molecules.apis.stack_api.publish") as mock_publish:
        await api.push_stack(stack_id, uuid4(), [])

        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.topic == "stack.pushed"
        assert event.entity_id == stack_id


@pytest.mark.unit
async def test_submit_stack_publishes_event() -> None:
    """Submit should publish STACK_SUBMITTED event."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github)
    stack_id = uuid4()

    api.entity.submit_stack = AsyncMock(
        return_value={
            "stack_id": str(stack_id),
            "results": [{"branch": "feature/1", "action": "created", "pr_number": 42}],
        }
    )

    with patch("molecules.apis.stack_api.publish") as mock_publish:
        await api.submit_stack(stack_id)

        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.topic == "stack.submitted"


@pytest.mark.unit
async def test_ready_stack_publishes_event() -> None:
    """Ready should publish STACK_MARKED_READY event."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github)
    stack_id = uuid4()

    api.entity.ready_stack = AsyncMock(
        return_value={
            "stack_id": str(stack_id),
            "results": [{"branch": "feature/1", "action": "marked_ready", "pr_number": 42}],
        }
    )

    with patch("molecules.apis.stack_api.publish") as mock_publish:
        await api.ready_stack(stack_id)

        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.topic == "stack.marked_ready"


@pytest.mark.unit
async def test_submit_stack_raises_without_github() -> None:
    """Submit without GitHubAdapter should raise RuntimeError."""
    db = AsyncMock()
    api = StackAPI(db)  # No github adapter

    with pytest.raises(RuntimeError, match="GitHubAdapter not configured"):
        await api.submit_stack(uuid4())


@pytest.mark.unit
async def test_ready_stack_raises_without_github() -> None:
    """Ready without GitHubAdapter should raise RuntimeError."""
    db = AsyncMock()
    api = StackAPI(db)  # No github adapter

    with pytest.raises(RuntimeError, match="GitHubAdapter not configured"):
        await api.ready_stack(uuid4())
