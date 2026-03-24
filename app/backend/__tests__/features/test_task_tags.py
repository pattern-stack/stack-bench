import pytest
from pydantic import ValidationError

from features.task_tags.models import TaskTag, task_tag_assignments
from features.task_tags.schemas.input import TaskTagCreate, TaskTagUpdate
from features.task_tags.schemas.output import TaskTagResponse
from features.task_tags.service import TaskTagService

# --- Model tests ---


@pytest.mark.unit
def test_task_tag_model_fields() -> None:
    """Verify all domain fields and sync fields exist on the model class."""
    # Domain fields
    assert hasattr(TaskTag, "name")
    assert hasattr(TaskTag, "color")
    assert hasattr(TaskTag, "description")
    assert hasattr(TaskTag, "group")
    assert hasattr(TaskTag, "is_exclusive")
    # External sync fields
    assert hasattr(TaskTag, "external_id")
    assert hasattr(TaskTag, "external_url")
    assert hasattr(TaskTag, "provider")
    assert hasattr(TaskTag, "last_synced_at")


@pytest.mark.unit
def test_task_tag_pattern_config() -> None:
    """Verify Pattern inner class: entity and reference_prefix (no state machine)."""
    assert TaskTag.Pattern.entity == "task_tag"
    assert TaskTag.Pattern.reference_prefix == "TTG"
    # BasePattern should NOT have states or initial_state
    assert not hasattr(TaskTag.Pattern, "states")
    assert not hasattr(TaskTag.Pattern, "initial_state")


@pytest.mark.unit
def test_task_tag_no_state_machine() -> None:
    """TaskTag uses BasePattern, not EventPattern - no state field."""
    assert not hasattr(TaskTag, "state")
    assert not hasattr(TaskTag, "transition_to")
    assert not hasattr(TaskTag, "can_transition_to")


@pytest.mark.unit
def test_task_tag_assignments_table() -> None:
    """Verify the association table exists with correct columns."""
    assert task_tag_assignments.name == "task_tag_assignments"
    col_names = {c.name for c in task_tag_assignments.columns}
    assert "task_id" in col_names
    assert "tag_id" in col_names


# --- Schema tests ---


@pytest.mark.unit
def test_task_tag_create_minimal() -> None:
    """TaskTagCreate with only required fields, verify defaults."""
    data = TaskTagCreate(name="bug")
    assert data.name == "bug"
    assert data.color is None
    assert data.description is None
    assert data.group is None
    assert data.is_exclusive is False
    assert data.provider == "local"
    assert data.external_id is None
    assert data.external_url is None
    assert data.last_synced_at is None


@pytest.mark.unit
def test_task_tag_create_full() -> None:
    """TaskTagCreate with all fields populated, verify round-trip."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)

    data = TaskTagCreate(
        name="critical",
        color="#ff0000",
        description="Critical priority items",
        group="priority",
        is_exclusive=True,
        external_id="LBL-42",
        external_url="https://github.com/org/repo/labels/critical",
        provider="github",
        last_synced_at=now,
    )
    assert data.name == "critical"
    assert data.color == "#ff0000"
    assert data.description == "Critical priority items"
    assert data.group == "priority"
    assert data.is_exclusive is True
    assert data.external_id == "LBL-42"
    assert data.external_url == "https://github.com/org/repo/labels/critical"
    assert data.provider == "github"
    assert data.last_synced_at == now


@pytest.mark.unit
def test_task_tag_create_requires_name() -> None:
    """Omitting name raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskTagCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_task_tag_create_rejects_empty_name() -> None:
    """Empty string name raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskTagCreate(name="")


@pytest.mark.unit
def test_task_tag_create_rejects_invalid_provider() -> None:
    """Invalid provider value raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskTagCreate(name="test", provider="jira")


@pytest.mark.unit
def test_task_tag_create_rejects_invalid_color() -> None:
    """Color longer than 7 chars raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskTagCreate(name="test", color="#ff00001")


@pytest.mark.unit
def test_task_tag_update_partial() -> None:
    """TaskTagUpdate with only name set, rest are None."""
    data = TaskTagUpdate(name="updated")
    assert data.name == "updated"
    assert data.color is None
    assert data.description is None
    assert data.group is None
    assert data.is_exclusive is None
    assert data.external_id is None
    assert data.external_url is None
    assert data.provider is None
    assert data.last_synced_at is None


@pytest.mark.unit
def test_task_tag_update_empty() -> None:
    """TaskTagUpdate with no fields is valid (all optional)."""
    data = TaskTagUpdate()
    assert data.name is None


@pytest.mark.unit
def test_task_tag_response_from_attributes() -> None:
    """Verify model_config has from_attributes=True."""
    assert TaskTagResponse.model_config.get("from_attributes") is True


# --- Service tests ---


@pytest.mark.unit
def test_task_tag_service_model() -> None:
    """Verify TaskTagService().model is TaskTag."""
    service = TaskTagService()
    assert service.model is TaskTag
