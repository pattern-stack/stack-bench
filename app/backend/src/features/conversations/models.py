from __future__ import annotations

from typing import Any
from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, RelationalPattern, StatePhase


class Conversation(EventPattern):
    __tablename__ = "conversations"

    class Pattern:
        entity = "conversation"
        reference_prefix = "CONV"
        initial_state = "created"
        states = {
            "created": ["active"],
            "active": ["completed", "failed"],
            "completed": [],
            "failed": [],
        }
        state_phases = {
            "created": StatePhase.INITIAL,
            "active": StatePhase.ACTIVE,
            "completed": StatePhase.SUCCESS,
            "failed": StatePhase.FAILURE,
        }
        emit_state_transitions = True
        track_changes = True

    agent_name = Field(str, required=True, max_length=100, index=True)
    model = Field(str, max_length=100, default="claude-sonnet-4-20250514")
    error_message = Field(str, nullable=True)
    metadata_ = Field(dict, default=dict)
    agent_config = Field(dict, nullable=True)
    exchange_count = Field(int, default=0, min=0)
    total_input_tokens = Field(int, default=0, min=0)
    total_output_tokens = Field(int, default=0, min=0)
    branched_from_id = Field(UUID, foreign_key="conversations.id", nullable=True, index=True)
    branched_at_sequence = Field(int, nullable=True)
    conversation_type = Field(
        str,
        default="execution",
        choices=["planning", "execution", "review"],
        max_length=20,
        index=True,
    )


class ConversationContext(RelationalPattern):
    __tablename__ = "conversation_contexts"

    class Pattern:
        entity = "conversation_context"
        reference_prefix = "CTX"
        track_changes = True

    def __init__(self, **kwargs: Any) -> None:
        # Accept domain-friendly kwargs and map to relational columns
        if "conversation_id" in kwargs:
            kwargs["entity_a_type"] = "conversation"
            kwargs["entity_a_id"] = kwargs.pop("conversation_id")
        if "target_type" in kwargs:
            kwargs["entity_b_type"] = kwargs.pop("target_type")
        if "target_id" in kwargs:
            kwargs["entity_b_id"] = kwargs.pop("target_id")
        if "role" in kwargs:
            kwargs["relationship_type"] = kwargs.pop("role")
        super().__init__(**kwargs)

    @property
    def conversation_id(self) -> UUID:
        return self.entity_a_id  # type: ignore[return-value]

    @property
    def entity_type(self) -> str:
        return self.entity_b_type  # type: ignore[return-value]

    @property
    def entity_id(self) -> UUID:
        return self.entity_b_id  # type: ignore[return-value]

    @property
    def role(self) -> str:
        return self.relationship_type  # type: ignore[return-value]
