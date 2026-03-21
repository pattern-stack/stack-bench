from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.messages.models import Message
from features.messages.schemas.input import MessageCreate, MessageUpdate
from features.messages.schemas.output import MessageResponse
from features.messages.service import MessageService


@pytest.mark.unit
def test_message_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(Message, "conversation_id")
    assert hasattr(Message, "kind")
    assert hasattr(Message, "sequence")
    assert hasattr(Message, "run_id")
    assert hasattr(Message, "input_tokens")
    assert hasattr(Message, "output_tokens")


@pytest.mark.unit
def test_message_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert Message.Pattern.entity == "message"
    assert Message.Pattern.reference_prefix == "MSG"


@pytest.mark.unit
def test_message_table_args() -> None:
    """Verify unique constraint on (conversation_id, sequence)."""
    constraints = Message.__table_args__
    assert len(constraints) == 1
    assert constraints[0].name == "uq_message_sequence"


@pytest.mark.unit
def test_message_create_schema() -> None:
    """Verify create schema with required fields."""
    conv_id = uuid4()
    data = MessageCreate(conversation_id=conv_id, kind="request", sequence=1)
    assert data.conversation_id == conv_id
    assert data.kind == "request"
    assert data.sequence == 1
    assert data.run_id is None


@pytest.mark.unit
def test_message_create_requires_fields() -> None:
    """Verify required fields are enforced."""
    with pytest.raises(ValidationError):
        MessageCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_message_create_rejects_empty_kind() -> None:
    """Verify empty kind is rejected."""
    with pytest.raises(ValidationError):
        MessageCreate(conversation_id=uuid4(), kind="", sequence=1)


@pytest.mark.unit
def test_message_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = MessageUpdate(input_tokens=150)
    assert data.input_tokens == 150
    assert data.output_tokens is None


@pytest.mark.unit
def test_message_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert MessageResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_message_service_model() -> None:
    """Verify service is configured with correct model."""
    service = MessageService()
    assert service.model is Message
