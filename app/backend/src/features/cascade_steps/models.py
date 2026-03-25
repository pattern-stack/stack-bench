from datetime import datetime
from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class CascadeStep(EventPattern):
    __tablename__ = "cascade_steps"

    class Pattern:
        entity = "cascade_step"
        reference_prefix = "CS"
        initial_state = "pending"
        states = {
            "pending": ["retargeting", "skipped"],
            "retargeting": ["rebasing", "failed"],
            "rebasing": ["ci_pending", "conflict", "failed"],
            "ci_pending": ["completing", "failed"],
            "completing": ["merged", "failed"],
            "merged": [],
            "conflict": [],
            "failed": [],
            "skipped": [],
        }
        state_phases = {
            "pending": StatePhase.INITIAL,
            "retargeting": StatePhase.ACTIVE,
            "rebasing": StatePhase.ACTIVE,
            "ci_pending": StatePhase.PENDING,
            "completing": StatePhase.PENDING,
            "merged": StatePhase.SUCCESS,
            "conflict": StatePhase.FAILURE,
            "failed": StatePhase.FAILURE,
            "skipped": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    cascade_id = Field(UUID, foreign_key="merge_cascades.id", required=True, index=True)
    branch_id = Field(UUID, foreign_key="branches.id", required=True, index=True)
    pull_request_id = Field(UUID, foreign_key="pull_requests.id", nullable=True, index=True)
    position = Field(int, required=True, min=1)
    check_run_external_id = Field(int, nullable=True)
    head_sha = Field(str, nullable=True, max_length=40)
    error = Field(str, nullable=True)
    started_at = Field(datetime, nullable=True)
    completed_at = Field(datetime, nullable=True)
