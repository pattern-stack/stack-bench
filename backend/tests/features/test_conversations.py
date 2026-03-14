import pytest
from pydantic import ValidationError

from features.conversations.models import Conversation
from features.conversations.schemas.input import ConversationCreate, ConversationUpdate
from features.conversations.schemas.output import ConversationResponse
from features.conversations.service import ConversationService


@pytest.mark.unit
def test_conversation_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(Conversation, "agent_name")
    assert hasattr(Conversation, "model")
    assert hasattr(Conversation, "state")
    assert hasattr(Conversation, "error_message")
    assert hasattr(Conversation, "metadata_")
    assert hasattr(Conversation, "agent_config")
    assert hasattr(Conversation, "exchange_count")
    assert hasattr(Conversation, "total_input_tokens")
    assert hasattr(Conversation, "total_output_tokens")
    assert hasattr(Conversation, "branched_from_id")
    assert hasattr(Conversation, "branched_at_sequence")


@pytest.mark.unit
def test_conversation_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert Conversation.Pattern.entity == "conversation"
    assert Conversation.Pattern.reference_prefix == "CONV"
    assert Conversation.Pattern.initial_state == "created"
    assert "created" in Conversation.Pattern.states
    assert "active" in Conversation.Pattern.states["created"]


@pytest.mark.unit
def test_conversation_state_machine() -> None:
    """Verify state machine transitions."""
    conv = Conversation()
    assert conv.state == "created"
    assert conv.can_transition_to("active")
    assert not conv.can_transition_to("completed")
    conv.transition_to("active")
    assert conv.state == "active"
    assert conv.can_transition_to("completed")
    assert conv.can_transition_to("failed")


@pytest.mark.unit
def test_conversation_invalid_transition() -> None:
    """Verify invalid transitions are rejected."""
    conv = Conversation()
    assert not conv.can_transition_to("completed")
    assert not conv.can_transition_to("failed")


@pytest.mark.unit
def test_conversation_full_lifecycle() -> None:
    """Verify full happy path: created -> active -> completed."""
    conv = Conversation()
    assert conv.state == "created"
    conv.transition_to("active")
    assert conv.state == "active"
    conv.transition_to("completed")
    assert conv.state == "completed"
    assert conv.get_allowed_transitions() == []


@pytest.mark.unit
def test_conversation_failure_path() -> None:
    """Verify failure path: created -> active -> failed."""
    conv = Conversation()
    conv.transition_to("active")
    conv.transition_to("failed")
    assert conv.state == "failed"
    assert conv.get_allowed_transitions() == []


@pytest.mark.unit
def test_conversation_create_schema() -> None:
    """Verify create schema with minimal data."""
    data = ConversationCreate(agent_name="understander")
    assert data.agent_name == "understander"
    assert data.model is None
    assert data.metadata_ is None
    assert data.agent_config is None


@pytest.mark.unit
def test_conversation_create_schema_full() -> None:
    """Verify create schema with all fields."""
    data = ConversationCreate(
        agent_name="understander",
        model="claude-opus-4-20250514",
        metadata_={"key": "value"},
        agent_config={"temperature": 0.7},
    )
    assert data.agent_name == "understander"
    assert data.model == "claude-opus-4-20250514"
    assert data.metadata_ == {"key": "value"}


@pytest.mark.unit
def test_conversation_create_requires_agent_name() -> None:
    """Verify agent_name is required."""
    with pytest.raises(ValidationError):
        ConversationCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_conversation_create_rejects_empty_agent_name() -> None:
    """Verify empty agent_name is rejected."""
    with pytest.raises(ValidationError):
        ConversationCreate(agent_name="")


@pytest.mark.unit
def test_conversation_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = ConversationUpdate(exchange_count=5)
    assert data.exchange_count == 5
    assert data.error_message is None


@pytest.mark.unit
def test_conversation_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert ConversationResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_conversation_service_model() -> None:
    """Verify service is configured with correct model."""
    service = ConversationService()
    assert service.model is Conversation
