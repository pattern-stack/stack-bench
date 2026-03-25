from datetime import datetime
from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class TaskProject(EventPattern):
    __tablename__ = "task_projects"

    class Pattern:
        entity = "task_project"
        reference_prefix = "TPJ"
        initial_state = "backlog"
        states = {
            "backlog": ["planning"],
            "planning": ["active"],
            "active": ["on_hold", "completed"],
            "on_hold": ["active"],
            "completed": ["archived"],
            "archived": [],
        }
        state_phases = {
            "backlog": StatePhase.INITIAL,
            "planning": StatePhase.PENDING,
            "active": StatePhase.ACTIVE,
            "on_hold": StatePhase.PENDING,
            "completed": StatePhase.SUCCESS,
            "archived": StatePhase.SUCCESS,
        }
        emit_state_transitions = True
        track_changes = True

    # Domain fields
    name = Field(str, required=True, max_length=500, index=True)
    description = Field(str, nullable=True)
    lead_id = Field(UUID, nullable=True, index=True)

    # External sync
    external_id = Field(str, nullable=True, max_length=200, index=True)
    external_url = Field(str, nullable=True, max_length=500)
    provider = Field(str, default="local", choices=["github", "linear", "local"])
    last_synced_at = Field(datetime, nullable=True)
