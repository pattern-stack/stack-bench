from uuid import uuid4

import pytest

from features.conversations.models import ConversationLink
from features.conversations.link_service import ConversationLinkService


@pytest.mark.unit
def test_conversation_link_model_fields() -> None:
    """Verify ConversationLink has RelationalPattern fields."""
    assert hasattr(ConversationLink, "entity_a_type")
    assert hasattr(ConversationLink, "entity_a_id")
    assert hasattr(ConversationLink, "entity_b_type")
    assert hasattr(ConversationLink, "entity_b_id")
    assert hasattr(ConversationLink, "relationship_type")
    assert hasattr(ConversationLink, "relationship_metadata")
    assert hasattr(ConversationLink, "is_active")
    assert hasattr(ConversationLink, "started_at")
    assert hasattr(ConversationLink, "ended_at")


@pytest.mark.unit
def test_conversation_link_pattern_config() -> None:
    """Verify Pattern inner class configuration."""
    assert ConversationLink.Pattern.entity == "conversation_link"
    assert ConversationLink.Pattern.reference_prefix == "CL"


@pytest.mark.unit
def test_conversation_link_construction() -> None:
    """Verify a ConversationLink can be constructed."""
    conv_id = uuid4()
    task_id = uuid4()
    link = ConversationLink(
        entity_a_type="conversation",
        entity_a_id=conv_id,
        entity_b_type="task",
        entity_b_id=task_id,
        relationship_type="execution",
        is_active=True,
    )
    assert link.entity_a_type == "conversation"
    assert link.entity_a_id == conv_id
    assert link.entity_b_type == "task"
    assert link.entity_b_id == task_id
    assert link.relationship_type == "execution"
    assert link.is_active is True


@pytest.mark.unit
def test_conversation_link_service_model() -> None:
    """Verify service is configured with correct model."""
    service = ConversationLinkService()
    assert service.model is ConversationLink


@pytest.mark.unit
def test_conversation_link_tablename() -> None:
    """Verify the table name is correct."""
    assert ConversationLink.__tablename__ == "conversation_links"
