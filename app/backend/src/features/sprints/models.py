from datetime import datetime
from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class Sprint(EventPattern):
    __tablename__ = "sprints"

    class Pattern:
        entity = "sprint"
        reference_prefix = "SPR"
        initial_state = "planned"
        states = {
            "planned": ["active"],
            "active": ["completed"],
            "completed": [],
        }
        state_phases = {
            "planned": StatePhase.INITIAL,
            "active": StatePhase.ACTIVE,
            "completed": StatePhase.SUCCESS,
        }
        emit_state_transitions = True
        track_changes = True

    # Domain fields
    name = Field(str, required=True, max_length=200, index=True)
    number = Field(int, nullable=True, index=True)
    description = Field(str, nullable=True)
    starts_at = Field(datetime, nullable=True)
    ends_at = Field(datetime, nullable=True)

    # Foreign keys
    project_id = Field(UUID, foreign_key="task_projects.id", nullable=True, index=True)

    # External sync
    external_id = Field(str, nullable=True, max_length=200, index=True)
    external_url = Field(str, nullable=True, max_length=500)
    provider = Field(str, default="local", choices=["github", "linear", "local"])
    last_synced_at = Field(datetime, nullable=True)
