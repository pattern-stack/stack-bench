from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.tool_calls.models import ToolCall
from features.tool_calls.schemas.input import ToolCallCreate, ToolCallUpdate
from features.tool_calls.schemas.output import ToolCallResponse
from features.tool_calls.service import ToolCallService


@pytest.mark.unit
def test_tool_call_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(ToolCall, "conversation_id")
    assert hasattr(ToolCall, "tool_call_id")
    assert hasattr(ToolCall, "tool_name")
    assert hasattr(ToolCall, "arguments")
    assert hasattr(ToolCall, "result")
    assert hasattr(ToolCall, "error")
    assert hasattr(ToolCall, "duration_ms")
    assert hasattr(ToolCall, "request_part_id")
    assert hasattr(ToolCall, "response_part_id")
    assert hasattr(ToolCall, "state")


@pytest.mark.unit
def test_tool_call_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert ToolCall.Pattern.entity == "tool_call"
    assert ToolCall.Pattern.reference_prefix == "TC"
    assert ToolCall.Pattern.initial_state == "pending"
    assert "pending" in ToolCall.Pattern.states
    assert "executed" in ToolCall.Pattern.states["pending"]
    assert "failed" in ToolCall.Pattern.states["pending"]


@pytest.mark.unit
def test_tool_call_state_machine() -> None:
    """Verify state machine transitions."""
    tc = ToolCall()
    assert tc.state == "pending"
    assert tc.can_transition_to("executed")
    assert tc.can_transition_to("failed")
    tc.transition_to("executed")
    assert tc.state == "executed"
    assert tc.get_allowed_transitions() == []


@pytest.mark.unit
def test_tool_call_failure_path() -> None:
    """Verify failure path: pending -> failed."""
    tc = ToolCall()
    tc.transition_to("failed")
    assert tc.state == "failed"
    assert tc.get_allowed_transitions() == []


@pytest.mark.unit
def test_tool_call_invalid_transition() -> None:
    """Verify invalid transitions are rejected."""
    tc = ToolCall()
    tc.transition_to("executed")
    assert not tc.can_transition_to("pending")
    assert not tc.can_transition_to("failed")


@pytest.mark.unit
def test_tool_call_create_schema() -> None:
    """Verify create schema with required fields."""
    conv_id = uuid4()
    data = ToolCallCreate(
        conversation_id=conv_id,
        tool_call_id="call_abc123",
        tool_name="read_file",
    )
    assert data.conversation_id == conv_id
    assert data.tool_call_id == "call_abc123"
    assert data.tool_name == "read_file"
    assert data.arguments is None


@pytest.mark.unit
def test_tool_call_create_with_arguments() -> None:
    """Verify create schema with optional fields."""
    conv_id = uuid4()
    part_id = uuid4()
    data = ToolCallCreate(
        conversation_id=conv_id,
        tool_call_id="call_abc123",
        tool_name="read_file",
        arguments={"path": "/tmp/test.py"},
        request_part_id=part_id,
    )
    assert data.arguments == {"path": "/tmp/test.py"}
    assert data.request_part_id == part_id


@pytest.mark.unit
def test_tool_call_create_requires_fields() -> None:
    """Verify required fields are enforced."""
    with pytest.raises(ValidationError):
        ToolCallCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_tool_call_create_rejects_empty_tool_name() -> None:
    """Verify empty tool_name is rejected."""
    with pytest.raises(ValidationError):
        ToolCallCreate(
            conversation_id=uuid4(),
            tool_call_id="call_123",
            tool_name="",
        )


@pytest.mark.unit
def test_tool_call_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = ToolCallUpdate(result="file contents here", duration_ms=150)
    assert data.result == "file contents here"
    assert data.duration_ms == 150
    assert data.error is None


@pytest.mark.unit
def test_tool_call_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert ToolCallResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_tool_call_service_model() -> None:
    """Verify service is configured with correct model."""
    service = ToolCallService()
    assert service.model is ToolCall
