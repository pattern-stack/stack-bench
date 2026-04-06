from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from molecules.apis.conversation_api import ConversationAPI


@pytest.fixture
def db() -> AsyncMock:
    mock = AsyncMock()
    mock.commit = AsyncMock()
    return mock


@pytest.fixture
def api(db: AsyncMock) -> ConversationAPI:
    return ConversationAPI(db)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_entity_returns_none_when_no_link(api: ConversationAPI) -> None:
    """Returns None when no link exists for the entity."""
    with patch.object(
        api.link_service,
        "get_conversation_for_entity",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await api.get_by_entity(
            entity_type="task",
            entity_id=uuid4(),
            role="execution",
        )
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_entity_returns_conversation_when_linked(api: ConversationAPI) -> None:
    """Returns the linked conversation response when a link exists."""
    conv_id = uuid4()
    task_id = uuid4()

    mock_link = MagicMock()
    mock_link.entity_a_id = conv_id

    mock_conv = MagicMock()
    mock_conv.id = conv_id
    mock_conv.reference_number = "CONV-001"
    mock_conv.agent_name = "orchestrator"
    mock_conv.model = "claude-sonnet-4-20250514"
    mock_conv.state = "active"
    mock_conv.conversation_type = "execution"
    mock_conv.error_message = None
    mock_conv.exchange_count = 5
    mock_conv.total_input_tokens = 1000
    mock_conv.total_output_tokens = 500
    mock_conv.project_id = uuid4()
    mock_conv.branched_from_id = None
    mock_conv.branched_at_sequence = None
    mock_conv.created_at = MagicMock()
    mock_conv.updated_at = MagicMock()

    with (
        patch.object(
            api.link_service,
            "get_conversation_for_entity",
            new_callable=AsyncMock,
            return_value=mock_link,
        ),
        patch.object(
            api.entity,
            "get_conversation",
            new_callable=AsyncMock,
            return_value=mock_conv,
        ),
    ):
        result = await api.get_by_entity(
            entity_type="task",
            entity_id=task_id,
            role="execution",
        )

    assert result is not None
    assert result.id == conv_id
    assert result.agent_name == "orchestrator"
