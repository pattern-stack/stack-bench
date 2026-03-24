from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class MergeCascade(EventPattern):
    __tablename__ = "merge_cascades"

    class Pattern:
        entity = "merge_cascade"
        reference_prefix = "MC"
        initial_state = "pending"
        states = {
            "pending": ["running", "cancelled"],
            "running": ["completed", "failed", "cancelled"],
            "completed": [],
            "failed": [],
            "cancelled": [],
        }
        state_phases = {
            "pending": StatePhase.INITIAL,
            "running": StatePhase.ACTIVE,
            "completed": StatePhase.SUCCESS,
            "failed": StatePhase.FAILURE,
            "cancelled": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    stack_id = Field(UUID, foreign_key="stacks.id", required=True, index=True)
    triggered_by = Field(str, required=True, max_length=200)
    current_position = Field(int, default=0)
    error = Field(str, nullable=True)
