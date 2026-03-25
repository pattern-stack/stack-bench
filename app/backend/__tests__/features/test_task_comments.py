from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.task_comments.models import TaskComment
from features.task_comments.schemas.input import TaskCommentCreate, TaskCommentUpdate
from features.task_comments.schemas.output import TaskCommentResponse
from features.task_comments.service import TaskCommentService

# --- Model tests ---


@pytest.mark.unit
def test_task_comment_model_fields() -> None:
    """Verify all domain fields, FK fields, and sync fields exist on the model class."""
    # Domain fields
    assert hasattr(TaskComment, "body")
    assert hasattr(TaskComment, "edited_at")
    # FK fields
    assert hasattr(TaskComment, "task_id")
    assert hasattr(TaskComment, "author_id")
    assert hasattr(TaskComment, "parent_id")
    # External sync fields
    assert hasattr(TaskComment, "external_id")
    assert hasattr(TaskComment, "external_url")
    assert hasattr(TaskComment, "provider")
    assert hasattr(TaskComment, "last_synced_at")


@pytest.mark.unit
def test_task_comment_pattern_config() -> None:
    """Verify Pattern inner class: entity and reference_prefix (no state machine)."""
    assert TaskComment.Pattern.entity == "task_comment"
    assert TaskComment.Pattern.reference_prefix == "TCM"
    # BasePattern should NOT have states or initial_state
    assert not hasattr(TaskComment.Pattern, "states")
    assert not hasattr(TaskComment.Pattern, "initial_state")


@pytest.mark.unit
def test_task_comment_no_state_machine() -> None:
    """TaskComment uses BasePattern, not EventPattern - no state field."""
    assert not hasattr(TaskComment, "state")
    assert not hasattr(TaskComment, "transition_to")
    assert not hasattr(TaskComment, "can_transition_to")


# --- Schema tests ---


@pytest.mark.unit
def test_task_comment_create_minimal() -> None:
    """TaskCommentCreate with only required fields, verify defaults."""
    task_id = uuid4()
    data = TaskCommentCreate(body="A comment", task_id=task_id)
    assert data.body == "A comment"
    assert data.task_id == task_id
    assert data.author_id is None
    assert data.parent_id is None
    assert data.provider == "local"
    assert data.external_id is None
    assert data.external_url is None
    assert data.last_synced_at is None


@pytest.mark.unit
def test_task_comment_create_full() -> None:
    """TaskCommentCreate with all fields populated, verify round-trip."""
    from datetime import UTC, datetime

    task_id = uuid4()
    author_id = uuid4()
    parent_id = uuid4()
    now = datetime.now(UTC)

    data = TaskCommentCreate(
        body="Full comment with **markdown**",
        task_id=task_id,
        author_id=author_id,
        parent_id=parent_id,
        external_id="IC-123",
        external_url="https://github.com/org/repo/issues/1#issuecomment-123",
        provider="github",
        last_synced_at=now,
    )
    assert data.body == "Full comment with **markdown**"
    assert data.task_id == task_id
    assert data.author_id == author_id
    assert data.parent_id == parent_id
    assert data.external_id == "IC-123"
    assert data.external_url == "https://github.com/org/repo/issues/1#issuecomment-123"
    assert data.provider == "github"
    assert data.last_synced_at == now


@pytest.mark.unit
def test_task_comment_create_requires_body() -> None:
    """Omitting body raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskCommentCreate(task_id=uuid4())  # type: ignore[call-arg]


@pytest.mark.unit
def test_task_comment_create_requires_task_id() -> None:
    """Omitting task_id raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskCommentCreate(body="A comment")  # type: ignore[call-arg]


@pytest.mark.unit
def test_task_comment_create_rejects_empty_body() -> None:
    """Empty string body raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskCommentCreate(body="", task_id=uuid4())


@pytest.mark.unit
def test_task_comment_create_rejects_invalid_provider() -> None:
    """Invalid provider value raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskCommentCreate(body="Test", task_id=uuid4(), provider="jira")


@pytest.mark.unit
def test_task_comment_update_partial() -> None:
    """TaskCommentUpdate with only body set, rest are None."""
    data = TaskCommentUpdate(body="Updated body")
    assert data.body == "Updated body"
    assert data.external_id is None
    assert data.external_url is None
    assert data.provider is None
    assert data.last_synced_at is None
    assert data.edited_at is None


@pytest.mark.unit
def test_task_comment_update_edited_at() -> None:
    """TaskCommentUpdate can set edited_at."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    data = TaskCommentUpdate(body="Edited", edited_at=now)
    assert data.edited_at == now


@pytest.mark.unit
def test_task_comment_response_from_attributes() -> None:
    """Verify model_config has from_attributes=True."""
    assert TaskCommentResponse.model_config.get("from_attributes") is True


# --- Service tests ---


@pytest.mark.unit
def test_task_comment_service_model() -> None:
    """Verify TaskCommentService().model is TaskComment."""
    service = TaskCommentService()
    assert service.model is TaskComment
