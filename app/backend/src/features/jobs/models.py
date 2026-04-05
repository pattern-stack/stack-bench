from typing import ClassVar
from uuid import UUID

from pattern_stack.atoms.capabilities import HistoryCapability
from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class Job(EventPattern):
    __tablename__ = "jobs"

    class Pattern:
        entity = "job"
        reference_prefix = "JOB"

        states: ClassVar = {
            "queued": ["running", "cancelled"],
            "running": ["gated", "complete", "failed", "cancelled"],
            "gated": ["running", "cancelled"],
            "complete": [],
            "failed": [],
            "cancelled": [],
        }
        initial_state = "queued"

        state_phases = {
            "queued": StatePhase.INITIAL,
            "running": StatePhase.ACTIVE,
            "gated": StatePhase.PENDING,
            "complete": StatePhase.SUCCESS,
            "failed": StatePhase.FAILURE,
            "cancelled": StatePhase.FAILURE,
        }

        history = HistoryCapability(
            track_changes=True,
            track_state=True,
            exclude=["updated_at"],
            retention="90d",
            expose_api=True,
        )

    task_id = Field(UUID, foreign_key="tasks.id", nullable=True, index=True)
    repo_url = Field(str, required=True, max_length=500)
    repo_branch = Field(str, required=True, max_length=200, default="main")
    issue_number = Field(int, nullable=True, index=True)
    issue_title = Field(str, nullable=True, max_length=500)
    issue_body = Field(str, nullable=True)
    current_phase = Field(str, nullable=True, max_length=50)
    input_text = Field(str, nullable=True)
    error_message = Field(str, nullable=True, max_length=2000)
    artifacts = Field(dict, default=dict, required=True)
    gate_decisions = Field(list, default=list, required=True)
    job_record_id = Field(UUID, nullable=True)
