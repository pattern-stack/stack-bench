from uuid import uuid4

import pytest

from features.conversations.models import ConversationContext
from features.conversations.service import ConversationService


@pytest.mark.unit
def test_conversation_context_model_fields() -> None:
    """Verify ConversationContext has RelationalPattern fields."""
    assert hasattr(ConversationContext, "entity_a_type")
    assert hasattr(ConversationContext, "entity_a_id")
    assert hasattr(ConversationContext, "entity_b_type")
    assert hasattr(ConversationContext, "entity_b_id")
    assert hasattr(ConversationContext, "relationship_type")
    assert hasattr(ConversationContext, "relationship_metadata")
    assert hasattr(ConversationContext, "is_active")
    assert hasattr(ConversationContext, "started_at")
    assert hasattr(ConversationContext, "ended_at")


@pytest.mark.unit
def test_conversation_context_pattern_config() -> None:
    """Verify Pattern inner class configuration."""
    assert ConversationContext.Pattern.entity == "conversation_context"
    assert ConversationContext.Pattern.reference_prefix == "CTX"


@pytest.mark.unit
def test_conversation_context_construction() -> None:
    """Verify a ConversationContext can be constructed."""
    conv_id = uuid4()
    task_id = uuid4()
    ctx = ConversationContext(
        entity_a_type="conversation",
        entity_a_id=conv_id,
        entity_b_type="task",
        entity_b_id=task_id,
        relationship_type="execution",
        is_active=True,
    )
    assert ctx.entity_a_type == "conversation"
    assert ctx.entity_a_id == conv_id
    assert ctx.entity_b_type == "task"
    assert ctx.entity_b_id == task_id
    assert ctx.relationship_type == "execution"
    assert ctx.is_active is True


@pytest.mark.unit
def test_conversation_service_model() -> None:
    """Verify service is configured with correct model."""
    service = ConversationService()
    assert service.model is not None


@pytest.mark.unit
def test_conversation_context_tablename() -> None:
    """Verify the table name is correct."""
    assert ConversationContext.__tablename__ == "conversation_contexts"
