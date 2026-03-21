from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class PullRequest(EventPattern):
    __tablename__ = "pull_requests"

    class Pattern:
        entity = "pull_request"
        reference_prefix = "PR"
        initial_state = "draft"
        states = {
            "draft": ["open"],
            "open": ["approved", "closed"],
            "approved": ["merged", "closed"],
            "merged": [],
            "closed": ["open"],
        }
        state_phases = {
            "draft": StatePhase.INITIAL,
            "open": StatePhase.ACTIVE,
            "approved": StatePhase.PENDING,
            "merged": StatePhase.SUCCESS,
            "closed": StatePhase.FAILURE,
        }
        emit_state_transitions = True
        track_changes = True

    branch_id = Field(UUID, foreign_key="branches.id", required=True, unique=True, index=True)
    external_id = Field(int, nullable=True)
    external_url = Field(str, nullable=True, max_length=500)
    title = Field(str, required=True, max_length=500)
    description = Field(str, nullable=True)
    review_notes = Field(str, nullable=True)
