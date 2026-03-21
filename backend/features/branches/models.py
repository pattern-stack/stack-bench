from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase
from sqlalchemy import UniqueConstraint


class Branch(EventPattern):
    __tablename__ = "branches"

    __table_args__ = (UniqueConstraint("stack_id", "position", name="uq_branch_stack_position"),)

    class Pattern:
        entity = "branch"
        reference_prefix = "BR"
        initial_state = "created"
        states = {
            "created": ["pushed"],
            "pushed": ["reviewing"],
            "reviewing": ["ready"],
            "ready": ["submitted"],
            "submitted": ["merged"],
            "merged": [],
        }
        state_phases = {
            "created": StatePhase.INITIAL,
            "pushed": StatePhase.ACTIVE,
            "reviewing": StatePhase.ACTIVE,
            "ready": StatePhase.PENDING,
            "submitted": StatePhase.PENDING,
            "merged": StatePhase.SUCCESS,
        }
        emit_state_transitions = True
        track_changes = True

    stack_id = Field(UUID, foreign_key="stacks.id", required=True, index=True)
    workspace_id = Field(UUID, foreign_key="workspaces.id", required=True, index=True)
    name = Field(str, required=True, max_length=500)
    position = Field(int, required=True, min=1)
    head_sha = Field(str, nullable=True, max_length=40)
