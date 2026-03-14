from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class ToolCall(EventPattern):  # type: ignore[misc]
    __tablename__ = "tool_calls"

    class Pattern:
        entity = "tool_call"
        reference_prefix = "TC"
        initial_state = "pending"
        states = {
            "pending": ["executed", "failed"],
            "executed": [],
            "failed": [],
        }
        state_phases = {
            "pending": StatePhase.PENDING,
            "executed": StatePhase.SUCCESS,
            "failed": StatePhase.FAILURE,
        }
        emit_state_transitions = True

    conversation_id = Field(UUID, foreign_key="conversations.id", required=True, index=True)
    tool_call_id = Field(str, required=True, max_length=200)
    tool_name = Field(str, required=True, max_length=200)
    arguments = Field(dict, nullable=True)
    result = Field(str, nullable=True)
    error = Field(str, nullable=True)
    duration_ms = Field(int, nullable=True, min=0)
    request_part_id = Field(UUID, foreign_key="message_parts.id", nullable=True)
    response_part_id = Field(UUID, foreign_key="message_parts.id", nullable=True)
