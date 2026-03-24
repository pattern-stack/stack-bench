from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.cascade_steps.models import CascadeStep
from features.cascade_steps.schemas.input import CascadeStepCreate, CascadeStepUpdate
from features.cascade_steps.schemas.output import CascadeStepResponse
from features.cascade_steps.service import CascadeStepService

# --- CascadeStep Model ---


@pytest.mark.unit
def test_cascade_step_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(CascadeStep, "cascade_id")
    assert hasattr(CascadeStep, "branch_id")
    assert hasattr(CascadeStep, "pull_request_id")
    assert hasattr(CascadeStep, "position")
    assert hasattr(CascadeStep, "check_run_external_id")
    assert hasattr(CascadeStep, "head_sha")
    assert hasattr(CascadeStep, "error")
    assert hasattr(CascadeStep, "started_at")
    assert hasattr(CascadeStep, "completed_at")
    assert hasattr(CascadeStep, "state")


@pytest.mark.unit
def test_cascade_step_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert CascadeStep.Pattern.entity == "cascade_step"
    assert CascadeStep.Pattern.reference_prefix == "CS"
    assert CascadeStep.Pattern.initial_state == "pending"
    assert "pending" in CascadeStep.Pattern.states
    assert "retargeting" in CascadeStep.Pattern.states
    assert "rebasing" in CascadeStep.Pattern.states
    assert "ci_pending" in CascadeStep.Pattern.states
    assert "completing" in CascadeStep.Pattern.states
    assert "merged" in CascadeStep.Pattern.states
    assert "conflict" in CascadeStep.Pattern.states
    assert "failed" in CascadeStep.Pattern.states
    assert "skipped" in CascadeStep.Pattern.states


@pytest.mark.unit
def test_cascade_step_state_machine_initial() -> None:
    """Verify state machine transitions from pending."""
    step = CascadeStep()
    assert step.state == "pending"
    assert step.can_transition_to("retargeting")
    assert step.can_transition_to("skipped")
    assert not step.can_transition_to("rebasing")
    assert not step.can_transition_to("merged")


@pytest.mark.unit
def test_cascade_step_invalid_transition() -> None:
    """Verify pending cannot skip to rebasing, ci_pending, completing, or merged."""
    step = CascadeStep()
    assert not step.can_transition_to("rebasing")
    assert not step.can_transition_to("ci_pending")
    assert not step.can_transition_to("completing")
    assert not step.can_transition_to("merged")
    assert not step.can_transition_to("conflict")
    assert not step.can_transition_to("failed")


@pytest.mark.unit
def test_cascade_step_full_lifecycle_merged() -> None:
    """Verify full lifecycle: pending -> retargeting -> rebasing -> ci_pending -> completing -> merged."""
    step = CascadeStep()
    assert step.state == "pending"
    step.transition_to("retargeting")
    assert step.state == "retargeting"
    step.transition_to("rebasing")
    assert step.state == "rebasing"
    step.transition_to("ci_pending")
    assert step.state == "ci_pending"
    step.transition_to("completing")
    assert step.state == "completing"
    step.transition_to("merged")
    assert step.state == "merged"
    assert step.get_allowed_transitions() == []


@pytest.mark.unit
def test_cascade_step_conflict_path() -> None:
    """Verify conflict path: pending -> retargeting -> rebasing -> conflict."""
    step = CascadeStep()
    step.transition_to("retargeting")
    step.transition_to("rebasing")
    step.transition_to("conflict")
    assert step.state == "conflict"
    assert step.get_allowed_transitions() == []


@pytest.mark.unit
def test_cascade_step_failure_from_retargeting() -> None:
    """Verify failure from retargeting."""
    step = CascadeStep()
    step.transition_to("retargeting")
    step.transition_to("failed")
    assert step.state == "failed"
    assert step.get_allowed_transitions() == []


@pytest.mark.unit
def test_cascade_step_failure_from_rebasing() -> None:
    """Verify failure from rebasing."""
    step = CascadeStep()
    step.transition_to("retargeting")
    step.transition_to("rebasing")
    step.transition_to("failed")
    assert step.state == "failed"


@pytest.mark.unit
def test_cascade_step_failure_from_ci_pending() -> None:
    """Verify failure from ci_pending."""
    step = CascadeStep()
    step.transition_to("retargeting")
    step.transition_to("rebasing")
    step.transition_to("ci_pending")
    step.transition_to("failed")
    assert step.state == "failed"


@pytest.mark.unit
def test_cascade_step_failure_from_completing() -> None:
    """Verify failure from completing."""
    step = CascadeStep()
    step.transition_to("retargeting")
    step.transition_to("rebasing")
    step.transition_to("ci_pending")
    step.transition_to("completing")
    step.transition_to("failed")
    assert step.state == "failed"


@pytest.mark.unit
def test_cascade_step_skipped() -> None:
    """Verify skipped from pending."""
    step = CascadeStep()
    step.transition_to("skipped")
    assert step.state == "skipped"
    assert step.get_allowed_transitions() == []


@pytest.mark.unit
def test_cascade_step_create_schema() -> None:
    """Verify create schema with minimal data."""
    data = CascadeStepCreate(
        cascade_id=uuid4(),
        branch_id=uuid4(),
        position=1,
    )
    assert data.pull_request_id is None
    assert data.check_run_external_id is None
    assert data.head_sha is None


@pytest.mark.unit
def test_cascade_step_create_requires_fields() -> None:
    """Verify required fields."""
    with pytest.raises(ValidationError):
        CascadeStepCreate()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        CascadeStepCreate(cascade_id=uuid4())  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        CascadeStepCreate(cascade_id=uuid4(), branch_id=uuid4())  # type: ignore[call-arg]


@pytest.mark.unit
def test_cascade_step_create_rejects_zero_position() -> None:
    """Verify position=0 is rejected."""
    with pytest.raises(ValidationError):
        CascadeStepCreate(
            cascade_id=uuid4(),
            branch_id=uuid4(),
            position=0,
        )


@pytest.mark.unit
def test_cascade_step_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = CascadeStepUpdate(head_sha="a" * 40)
    assert data.head_sha == "a" * 40
    assert data.error is None


@pytest.mark.unit
def test_cascade_step_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert CascadeStepResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_cascade_step_service_model() -> None:
    """Verify service is configured with correct model."""
    service = CascadeStepService()
    assert service.model is CascadeStep
