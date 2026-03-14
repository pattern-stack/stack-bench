from unittest.mock import AsyncMock

import pytest

from molecules.entities.conversation_entity import ConversationEntity


@pytest.mark.unit
def test_conversation_entity_init() -> None:
    """Verify entity composes correct services."""
    db = AsyncMock()
    entity = ConversationEntity(db)
    assert entity.db is db
    assert entity.conversation_service is not None
    assert entity.message_service is not None
    assert entity.message_part_service is not None
    assert entity.tool_call_service is not None
    assert entity.assembler is not None


@pytest.mark.unit
def test_conversation_entity_services_are_correct_types() -> None:
    """Verify entity uses the correct service classes."""
    from features.conversations.service import ConversationService
    from features.message_parts.service import MessagePartService
    from features.messages.service import MessageService
    from features.tool_calls.service import ToolCallService
    from molecules.agents.assembler import AgentAssembler

    db = AsyncMock()
    entity = ConversationEntity(db)
    assert isinstance(entity.conversation_service, ConversationService)
    assert isinstance(entity.message_service, MessageService)
    assert isinstance(entity.message_part_service, MessagePartService)
    assert isinstance(entity.tool_call_service, ToolCallService)
    assert isinstance(entity.assembler, AgentAssembler)


@pytest.mark.unit
async def test_get_conversation_filters_soft_deleted() -> None:
    """Soft-deleted conversations should raise NotFoundError."""
    from unittest.mock import MagicMock
    from uuid import uuid4

    from molecules.exceptions import ConversationNotFoundError

    db = AsyncMock()
    entity = ConversationEntity(db)

    # Mock a soft-deleted conversation
    deleted_conv = MagicMock()
    deleted_conv.is_deleted = True
    entity.conversation_service.get = AsyncMock(return_value=deleted_conv)

    with pytest.raises(ConversationNotFoundError):
        await entity.get_conversation(uuid4())
