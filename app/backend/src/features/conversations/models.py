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
    project_id = Field(UUID, foreign_key="projects.id", nullable=True, index=True)
    branched_from_id = Field(UUID, foreign_key="conversations.id", nullable=True, index=True)
    branched_at_sequence = Field(int, nullable=True)
    conversation_type = Field(
        str,
        default="execution",
        choices=["planning", "execution", "review"],
        max_length=20,
        index=True,
    )


class ConversationLink(RelationalPattern):
    __tablename__ = "conversation_links"

    class Pattern:
        entity = "conversation_link"
        reference_prefix = "CL"
        track_changes = True
