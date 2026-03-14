from typing import ClassVar
from uuid import UUID

from pattern_stack.atoms.capabilities import HistoryCapability
from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class AgentRun(EventPattern):  # type: ignore[misc]
    __tablename__ = "agent_runs"

    class Pattern:
        entity = "agent_run"
        reference_prefix = "RUN"

        states: ClassVar = {
            "pending": ["running"],
            "running": ["complete", "failed"],
            "complete": [],
            "failed": [],
        }
        initial_state = "pending"

        state_phases = {
            "pending": StatePhase.INITIAL,
            "running": StatePhase.ACTIVE,
            "complete": StatePhase.SUCCESS,
            "failed": StatePhase.FAILURE,
        }

        history = HistoryCapability(
            track_changes=True,
            track_state=True,
            retention="90d",
        )

    job_id = Field(UUID, required=True, index=True, foreign_key="jobs.id")
    phase = Field(str, required=True, max_length=50)
    runner_type = Field(str, required=True, max_length=50)
    model_used = Field(str, nullable=True, max_length=100)
    input_tokens = Field(int, default=0)
    output_tokens = Field(int, default=0)
    artifact = Field(str, nullable=True)
    error_message = Field(str, nullable=True, max_length=2000)
    duration_ms = Field(int, nullable=True)
    attempt = Field(int, default=1)
