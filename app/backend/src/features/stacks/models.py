from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class Stack(EventPattern):
    __tablename__ = "stacks"

    class Pattern:
        entity = "stack"
        reference_prefix = "STK"
        initial_state = "draft"
        states = {
            "draft": ["active"],
            "active": ["submitted", "closed"],
            "submitted": ["merged", "closed"],
            "merged": [],
            "closed": [],
        }
        state_phases = {
            "draft": StatePhase.INITIAL,
            "active": StatePhase.ACTIVE,
            "submitted": StatePhase.PENDING,
            "merged": StatePhase.SUCCESS,
            "closed": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    project_id = Field(UUID, foreign_key="projects.id", required=True, index=True)
    name = Field(str, required=True, max_length=200, index=True)
    base_branch_id = Field(UUID, foreign_key="branches.id", nullable=True, index=True)
    trunk = Field(str, required=True, max_length=200, default="main")
