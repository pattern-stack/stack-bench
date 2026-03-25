from datetime import datetime
from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class Task(EventPattern):
    __tablename__ = "tasks"

    class Pattern:
        entity = "task"
        reference_prefix = "TSK"
        initial_state = "backlog"
        states = {
            "backlog": ["ready", "cancelled"],
            "ready": ["in_progress", "cancelled"],
            "in_progress": ["in_review", "cancelled"],
            "in_review": ["done", "in_progress", "cancelled"],
            "done": [],
            "cancelled": [],
        }
        state_phases = {
            "backlog": StatePhase.INITIAL,
            "ready": StatePhase.PENDING,
            "in_progress": StatePhase.ACTIVE,
            "in_review": StatePhase.PENDING,
            "done": StatePhase.SUCCESS,
            "cancelled": StatePhase.FAILURE,
        }
        emit_state_transitions = True
        track_changes = True

    # Domain fields
    title = Field(str, required=True, max_length=500, index=True)
    description = Field(str, nullable=True)
    priority = Field(str, default="none", choices=["critical", "high", "medium", "low", "none"])
    issue_type = Field(str, default="task", choices=["story", "bug", "task", "spike", "epic"])
    work_phase = Field(str, nullable=True, choices=["design", "build", "test", "deploy", "review"])
    status_category = Field(str, default="todo", choices=["todo", "in_progress", "done"])

    # Foreign keys
    project_id = Field(UUID, foreign_key="task_projects.id", nullable=True, index=True)
    assignee_id = Field(UUID, nullable=True, index=True)
    sprint_id = Field(UUID, foreign_key="sprints.id", nullable=True, index=True)

    # External sync
    external_id = Field(str, nullable=True, max_length=200, index=True)
    external_url = Field(str, nullable=True, max_length=500)
    provider = Field(str, default="local", choices=["github", "linear", "local"])
    last_synced_at = Field(datetime, nullable=True)
