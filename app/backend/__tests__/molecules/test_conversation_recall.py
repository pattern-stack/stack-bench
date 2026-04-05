"""Tests for conversation recall: list_filtered, branch, and ConversationAPI.branch facade."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from molecules.apis.conversation_api import ConversationAPI
from molecules.entities.conversation_entity import ConversationEntity


@pytest.mark.unit
async def test_list_filtered_with_agent_name() -> None:
    """list_filtered passes agent_name filter to service.list."""
    db = AsyncMock()
    entity = ConversationEntity(db)

    mock_conv = MagicMock()
    entity.conversation_service.list = AsyncMock(return_value=([mock_conv], 1))

    result, count = await entity.list_filtered(agent_name="architect")

    assert count == 1
    assert result == [mock_conv]
    entity.conversation_service.list.assert_awaited_once_with(
        db,
        offset=0,
        limit=100,
        filters={"agent_name": "architect"},
        order_by=["-created_at"],
    )


@pytest.mark.unit
async def test_list_filtered_with_state() -> None:
    """list_filtered passes state filter to service.list."""
    db = AsyncMock()
    entity = ConversationEntity(db)

    entity.conversation_service.list = AsyncMock(return_value=([], 0))

    result, count = await entity.list_filtered(state="active")

    assert count == 0
    assert result == []
    entity.conversation_service.list.assert_awaited_once_with(
        db,
        offset=0,
        limit=100,
        filters={"state": "active"},
        order_by=["-created_at"],
    )


@pytest.mark.unit
async def test_branch_conversation_copies_messages_up_to_sequence() -> None:
    """branch_conversation copies messages up to the given sequence number."""
    db = AsyncMock()
    entity = ConversationEntity(db)

    source_id = uuid4()
    branch_id = uuid4()

    # Mock source conversation
    source_conv = MagicMock()
    source_conv.id = source_id
    source_conv.agent_name = "architect"
    source_conv.model = "claude-sonnet-4-20250514"
    source_conv.agent_config = {"role_name": "architect"}
    source_conv.is_deleted = False

    # Mock branch conversation
    branch_conv = MagicMock()
    branch_conv.id = branch_id

    entity.conversation_service.get = AsyncMock(return_value=source_conv)
    entity.conversation_service.create = AsyncMock(return_value=branch_conv)

    # Build messages: seq 1, 2, 3 — branch at seq 2 should copy 1 and 2
    def make_msg(seq: int) -> MagicMock:
        msg = MagicMock()
        msg.sequence = seq
        msg.kind = "request" if seq % 2 == 1 else "response"
        msg.input_tokens = 100
        msg.output_tokens = 50
        return msg

    def make_part(content: str) -> MagicMock:
        part = MagicMock()
        part.part_type = "text"
        part.content = content
        part.tool_call_id = None
        part.tool_name = None
        part.tool_arguments = None
        return part

    messages_data = [
        {"message": make_msg(1), "parts": [make_part("hello")]},
        {"message": make_msg(2), "parts": [make_part("response")]},
        {"message": make_msg(3), "parts": [make_part("follow-up")]},
    ]

    entity.get_with_messages = AsyncMock(
        return_value={
            "conversation": source_conv,
            "messages": messages_data,
            "tool_calls": [],
        }
    )

    entity.add_message = AsyncMock()

    result = await entity.branch_conversation(source_id, at_sequence=2)

    assert result is branch_conv
    # Should have copied 2 messages (seq 1 and 2), not seq 3
    assert entity.add_message.await_count == 2


@pytest.mark.unit
async def test_branch_conversation_sets_branched_from_fields() -> None:
    """branch_conversation sets branched_from_id and branched_at_sequence."""
    db = AsyncMock()
    entity = ConversationEntity(db)

    source_id = uuid4()
    source_conv = MagicMock()
    source_conv.id = source_id
    source_conv.agent_name = "builder"
    source_conv.model = "claude-sonnet-4-20250514"
    source_conv.agent_config = {"role_name": "builder"}
    source_conv.is_deleted = False

    branch_conv = MagicMock()
    entity.conversation_service.get = AsyncMock(return_value=source_conv)
    entity.conversation_service.create = AsyncMock(return_value=branch_conv)
    entity.get_with_messages = AsyncMock(
        return_value={
            "conversation": source_conv,
            "messages": [],
            "tool_calls": [],
        }
    )

    await entity.branch_conversation(source_id, at_sequence=1)

    # Verify the create call includes branched_from_id and branched_at_sequence
    create_call = entity.conversation_service.create.call_args
    schema = create_call[0][1]  # positional arg: (db, schema)
    assert schema.branched_from_id == source_id
    assert schema.branched_at_sequence == 1


@pytest.mark.unit
async def test_conversation_api_branch_facade() -> None:
    """ConversationAPI.branch delegates to entity and commits."""
    db = AsyncMock()
    api = ConversationAPI(db)

    conv_id = uuid4()
    mock_conv = MagicMock()
    mock_conv.id = uuid4()
    mock_conv.reference_number = None
    mock_conv.agent_name = "architect"
    mock_conv.model = "claude-sonnet-4-20250514"
    mock_conv.state = "created"
    mock_conv.conversation_type = "execution"
    mock_conv.error_message = None
    mock_conv.exchange_count = 0
    mock_conv.total_input_tokens = 0
    mock_conv.total_output_tokens = 0
    mock_conv.project_id = uuid4()
    mock_conv.branched_from_id = conv_id
    mock_conv.branched_at_sequence = 3
    mock_conv.created_at = MagicMock()
    mock_conv.updated_at = MagicMock()

    with patch.object(api.entity, "branch_conversation", new_callable=AsyncMock, return_value=mock_conv):
        result = await api.branch(conv_id, at_sequence=3)

    assert result.branched_from_id == conv_id
    assert result.branched_at_sequence == 3
    db.commit.assert_awaited_once()
