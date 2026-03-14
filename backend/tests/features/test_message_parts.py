from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.message_parts.models import MessagePart
from features.message_parts.schemas.input import MessagePartCreate, MessagePartUpdate
from features.message_parts.schemas.output import MessagePartResponse
from features.message_parts.service import MessagePartService


@pytest.mark.unit
def test_message_part_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(MessagePart, "message_id")
    assert hasattr(MessagePart, "position")
    assert hasattr(MessagePart, "part_type")
    assert hasattr(MessagePart, "content")
    assert hasattr(MessagePart, "tool_call_id")
    assert hasattr(MessagePart, "tool_name")
    assert hasattr(MessagePart, "tool_arguments")


@pytest.mark.unit
def test_message_part_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert MessagePart.Pattern.entity == "message_part"
    assert MessagePart.Pattern.reference_prefix == "MPART"


@pytest.mark.unit
def test_message_part_table_args() -> None:
    """Verify unique constraint on (message_id, position)."""
    constraints = MessagePart.__table_args__
    assert len(constraints) == 1
    assert constraints[0].name == "uq_message_part_position"


@pytest.mark.unit
def test_message_part_create_schema() -> None:
    """Verify create schema with required fields."""
    msg_id = uuid4()
    data = MessagePartCreate(message_id=msg_id, position=0, part_type="text")
    assert data.message_id == msg_id
    assert data.position == 0
    assert data.part_type == "text"
    assert data.content is None


@pytest.mark.unit
def test_message_part_create_with_tool_data() -> None:
    """Verify create schema with tool call data."""
    msg_id = uuid4()
    data = MessagePartCreate(
        message_id=msg_id,
        position=1,
        part_type="tool_call",
        tool_call_id="call_123",
        tool_name="read_file",
        tool_arguments={"path": "/tmp/test.py"},
    )
    assert data.tool_name == "read_file"
    assert data.tool_arguments == {"path": "/tmp/test.py"}


@pytest.mark.unit
def test_message_part_create_requires_fields() -> None:
    """Verify required fields are enforced."""
    with pytest.raises(ValidationError):
        MessagePartCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_message_part_create_rejects_empty_part_type() -> None:
    """Verify empty part_type is rejected."""
    with pytest.raises(ValidationError):
        MessagePartCreate(message_id=uuid4(), position=0, part_type="")


@pytest.mark.unit
def test_message_part_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = MessagePartUpdate(content="updated content")
    assert data.content == "updated content"
    assert data.tool_name is None


@pytest.mark.unit
def test_message_part_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert MessagePartResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_message_part_service_model() -> None:
    """Verify service is configured with correct model."""
    service = MessagePartService()
    assert service.model is MessagePart
