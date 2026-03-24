from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.merge_cascades.models import MergeCascade
from features.merge_cascades.schemas.input import MergeCascadeCreate, MergeCascadeUpdate
from features.merge_cascades.schemas.output import MergeCascadeResponse
from features.merge_cascades.service import MergeCascadeService

# --- MergeCascade Model ---


@pytest.mark.unit
def test_merge_cascade_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(MergeCascade, "stack_id")
    assert hasattr(MergeCascade, "triggered_by")
    assert hasattr(MergeCascade, "current_position")
    assert hasattr(MergeCascade, "error")
    assert hasattr(MergeCascade, "state")


@pytest.mark.unit
def test_merge_cascade_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert MergeCascade.Pattern.entity == "merge_cascade"
    assert MergeCascade.Pattern.reference_prefix == "MC"
    assert MergeCascade.Pattern.initial_state == "pending"
    assert "pending" in MergeCascade.Pattern.states
    assert "running" in MergeCascade.Pattern.states
    assert "completed" in MergeCascade.Pattern.states
    assert "failed" in MergeCascade.Pattern.states
    assert "cancelled" in MergeCascade.Pattern.states


@pytest.mark.unit
def test_merge_cascade_state_machine() -> None:
    """Verify state machine transitions from pending."""
    cascade = MergeCascade()
    assert cascade.state == "pending"
    assert cascade.can_transition_to("running")
    assert cascade.can_transition_to("cancelled")
    cascade.transition_to("running")
    assert cascade.state == "running"
    assert cascade.can_transition_to("completed")
    assert cascade.can_transition_to("failed")
    assert cascade.can_transition_to("cancelled")


@pytest.mark.unit
def test_merge_cascade_invalid_transition() -> None:
    """Verify pending cannot transition to completed, failed directly."""
    cascade = MergeCascade()
    assert not cascade.can_transition_to("completed")
    assert not cascade.can_transition_to("failed")


@pytest.mark.unit
def test_merge_cascade_full_lifecycle_success() -> None:
    """Verify full lifecycle: pending -> running -> completed."""
    cascade = MergeCascade()
    assert cascade.state == "pending"
    cascade.transition_to("running")
    assert cascade.state == "running"
    cascade.transition_to("completed")
    assert cascade.state == "completed"
    assert cascade.get_allowed_transitions() == []


@pytest.mark.unit
def test_merge_cascade_failure_path() -> None:
    """Verify failure path: pending -> running -> failed."""
    cascade = MergeCascade()
    cascade.transition_to("running")
    cascade.transition_to("failed")
    assert cascade.state == "failed"
    assert cascade.get_allowed_transitions() == []


@pytest.mark.unit
def test_merge_cascade_cancellation_from_pending() -> None:
    """Verify cancellation from pending."""
    cascade = MergeCascade()
    cascade.transition_to("cancelled")
    assert cascade.state == "cancelled"
    assert cascade.get_allowed_transitions() == []


@pytest.mark.unit
def test_merge_cascade_cancellation_from_running() -> None:
    """Verify cancellation from running."""
    cascade = MergeCascade()
    cascade.transition_to("running")
    cascade.transition_to("cancelled")
    assert cascade.state == "cancelled"
    assert cascade.get_allowed_transitions() == []


@pytest.mark.unit
def test_merge_cascade_create_schema() -> None:
    """Verify create schema with minimal data."""
    data = MergeCascadeCreate(stack_id=uuid4(), triggered_by="merge_pr_42")
    assert data.current_position == 0


@pytest.mark.unit
def test_merge_cascade_create_requires_fields() -> None:
    """Verify required fields."""
    with pytest.raises(ValidationError):
        MergeCascadeCreate()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        MergeCascadeCreate(stack_id=uuid4())  # type: ignore[call-arg]


@pytest.mark.unit
def test_merge_cascade_create_rejects_empty_triggered_by() -> None:
    """Verify empty triggered_by is rejected."""
    with pytest.raises(ValidationError):
        MergeCascadeCreate(stack_id=uuid4(), triggered_by="")


@pytest.mark.unit
def test_merge_cascade_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = MergeCascadeUpdate(current_position=3)
    assert data.current_position == 3
    assert data.error is None


@pytest.mark.unit
def test_merge_cascade_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert MergeCascadeResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_merge_cascade_service_model() -> None:
    """Verify service is configured with correct model."""
    service = MergeCascadeService()
    assert service.model is MergeCascade
