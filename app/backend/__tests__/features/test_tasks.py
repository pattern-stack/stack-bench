from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.tasks.models import Task
from features.tasks.schemas.input import TaskCreate, TaskUpdate
from features.tasks.schemas.output import TaskResponse
from features.tasks.service import TaskService

# --- Model tests ---


@pytest.mark.unit
def test_task_model_fields() -> None:
    """Verify all domain fields, FK fields, and sync fields exist on the model class."""
    # Domain fields
    assert hasattr(Task, "title")
    assert hasattr(Task, "description")
    assert hasattr(Task, "priority")
    assert hasattr(Task, "issue_type")
    assert hasattr(Task, "work_phase")
    assert hasattr(Task, "status_category")
    # FK fields
    assert hasattr(Task, "project_id")
    assert hasattr(Task, "assignee_id")
    assert hasattr(Task, "sprint_id")
    # External sync fields
    assert hasattr(Task, "external_id")
    assert hasattr(Task, "external_url")
    assert hasattr(Task, "provider")
    assert hasattr(Task, "last_synced_at")
    # EventPattern fields
    assert hasattr(Task, "state")


@pytest.mark.unit
def test_task_pattern_config() -> None:
    """Verify Pattern inner class: entity, reference_prefix, initial_state, all state keys."""
    assert Task.Pattern.entity == "task"
    assert Task.Pattern.reference_prefix == "TSK"
    assert Task.Pattern.initial_state == "backlog"
    assert "backlog" in Task.Pattern.states
    assert "ready" in Task.Pattern.states
    assert "in_progress" in Task.Pattern.states
    assert "in_review" in Task.Pattern.states
    assert "done" in Task.Pattern.states
    assert "cancelled" in Task.Pattern.states


@pytest.mark.unit
def test_task_initial_state() -> None:
    """Instantiate Task(), assert state is 'backlog'."""
    task = Task()
    assert task.state == "backlog"


@pytest.mark.unit
def test_task_state_machine_happy_path() -> None:
    """Walk backlog -> ready -> in_progress -> in_review -> done."""
    task = Task()
    assert task.state == "backlog"

    assert task.can_transition_to("ready")
    task.transition_to("ready")
    assert task.state == "ready"

    assert task.can_transition_to("in_progress")
    task.transition_to("in_progress")
    assert task.state == "in_progress"

    assert task.can_transition_to("in_review")
    task.transition_to("in_review")
    assert task.state == "in_review"

    assert task.can_transition_to("done")
    task.transition_to("done")
    assert task.state == "done"


@pytest.mark.unit
def test_task_cancelled_from_each_state() -> None:
    """Verify cancellation is reachable from backlog, ready, in_progress, in_review."""
    for start_states in [
        [],  # backlog
        ["ready"],
        ["ready", "in_progress"],
        ["ready", "in_progress", "in_review"],
    ]:
        task = Task()
        for s in start_states:
            task.transition_to(s)
        assert task.can_transition_to("cancelled")
        task.transition_to("cancelled")
        assert task.state == "cancelled"


@pytest.mark.unit
def test_task_invalid_transitions() -> None:
    """Verify backlog cannot jump to in_progress, done, or in_review directly."""
    task = Task()
    assert not task.can_transition_to("in_progress")
    assert not task.can_transition_to("done")
    assert not task.can_transition_to("in_review")


@pytest.mark.unit
def test_task_rework_path() -> None:
    """Verify in_review -> in_progress (rework), then back to in_review -> done."""
    task = Task()
    task.transition_to("ready")
    task.transition_to("in_progress")
    task.transition_to("in_review")
    assert task.state == "in_review"

    # Rework
    assert task.can_transition_to("in_progress")
    task.transition_to("in_progress")
    assert task.state == "in_progress"

    # Back to review and done
    task.transition_to("in_review")
    task.transition_to("done")
    assert task.state == "done"


@pytest.mark.unit
def test_task_terminal_states() -> None:
    """Verify done and cancelled have no allowed transitions."""
    # Done is terminal
    task_done = Task()
    task_done.transition_to("ready")
    task_done.transition_to("in_progress")
    task_done.transition_to("in_review")
    task_done.transition_to("done")
    assert task_done.get_allowed_transitions() == []

    # Cancelled is terminal
    task_cancelled = Task()
    task_cancelled.transition_to("cancelled")
    assert task_cancelled.get_allowed_transitions() == []


# --- Schema tests ---


@pytest.mark.unit
def test_task_create_minimal() -> None:
    """TaskCreate with only title, verify defaults."""
    data = TaskCreate(title="My task")
    assert data.title == "My task"
    assert data.priority == "none"
    assert data.issue_type == "task"
    assert data.provider == "local"
    assert data.status_category == "todo"
    assert data.description is None
    assert data.project_id is None
    assert data.assignee_id is None
    assert data.sprint_id is None


@pytest.mark.unit
def test_task_create_full() -> None:
    """TaskCreate with all fields populated, verify round-trip."""
    from datetime import UTC, datetime

    project_id = uuid4()
    assignee_id = uuid4()
    sprint_id = uuid4()
    now = datetime.now(UTC)

    data = TaskCreate(
        title="Full task",
        description="A detailed description",
        priority="high",
        issue_type="bug",
        work_phase="build",
        status_category="in_progress",
        project_id=project_id,
        assignee_id=assignee_id,
        sprint_id=sprint_id,
        external_id="GH-42",
        external_url="https://github.com/org/repo/issues/42",
        provider="github",
        last_synced_at=now,
    )
    assert data.title == "Full task"
    assert data.description == "A detailed description"
    assert data.priority == "high"
    assert data.issue_type == "bug"
    assert data.work_phase == "build"
    assert data.status_category == "in_progress"
    assert data.project_id == project_id
    assert data.assignee_id == assignee_id
    assert data.sprint_id == sprint_id
    assert data.external_id == "GH-42"
    assert data.external_url == "https://github.com/org/repo/issues/42"
    assert data.provider == "github"
    assert data.last_synced_at == now


@pytest.mark.unit
def test_task_create_requires_title() -> None:
    """Omitting title raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_task_create_rejects_empty_title() -> None:
    """Empty string title raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskCreate(title="")


@pytest.mark.unit
def test_task_create_rejects_invalid_priority() -> None:
    """Invalid priority value raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskCreate(title="Test", priority="urgent")


@pytest.mark.unit
def test_task_create_rejects_invalid_provider() -> None:
    """Invalid provider value raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskCreate(title="Test", provider="jira")


@pytest.mark.unit
def test_task_update_partial() -> None:
    """TaskUpdate with only title set, rest are None."""
    data = TaskUpdate(title="Updated title")
    assert data.title == "Updated title"
    assert data.description is None
    assert data.priority is None
    assert data.issue_type is None
    assert data.work_phase is None
    assert data.status_category is None
    assert data.project_id is None
    assert data.assignee_id is None
    assert data.sprint_id is None


@pytest.mark.unit
def test_task_response_from_attributes() -> None:
    """Verify model_config has from_attributes=True."""
    assert TaskResponse.model_config.get("from_attributes") is True


# --- Service tests ---


@pytest.mark.unit
def test_task_service_model() -> None:
    """Verify TaskService().model is Task."""
    service = TaskService()
    assert service.model is Task
