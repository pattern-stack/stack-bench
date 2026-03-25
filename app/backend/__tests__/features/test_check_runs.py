from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.check_runs.models import CheckRun
from features.check_runs.schemas.input import CheckRunCreate, CheckRunUpdate
from features.check_runs.schemas.output import CheckRunResponse
from features.check_runs.service import CheckRunService

# --- CheckRun Model ---


@pytest.mark.unit
def test_check_run_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(CheckRun, "pull_request_id")
    assert hasattr(CheckRun, "external_id")
    assert hasattr(CheckRun, "head_sha")
    assert hasattr(CheckRun, "name")
    assert hasattr(CheckRun, "status")
    assert hasattr(CheckRun, "conclusion")


@pytest.mark.unit
def test_check_run_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert CheckRun.Pattern.entity == "check_run"
    assert CheckRun.Pattern.reference_prefix == "CHK"
    assert CheckRun.Pattern.track_changes is True


@pytest.mark.unit
def test_check_run_is_base_pattern() -> None:
    """Verify CheckRun uses BasePattern (no state machine)."""
    from pattern_stack.atoms.patterns import BasePattern

    assert issubclass(CheckRun, BasePattern)
    # BasePattern has no state machine
    assert not hasattr(CheckRun, "can_transition_to") or not hasattr(CheckRun.Pattern, "states")


@pytest.mark.unit
def test_check_run_create_schema() -> None:
    """Verify create schema with all required fields."""
    data = CheckRunCreate(
        pull_request_id=uuid4(),
        external_id=123456789,
        head_sha="a" * 40,
        name="CI / test",
        status="queued",
    )
    assert data.conclusion is None


@pytest.mark.unit
def test_check_run_create_with_conclusion() -> None:
    """Verify create schema with conclusion."""
    data = CheckRunCreate(
        pull_request_id=uuid4(),
        external_id=123456789,
        head_sha="a" * 40,
        name="CI / test",
        status="completed",
        conclusion="success",
    )
    assert data.conclusion == "success"


@pytest.mark.unit
def test_check_run_create_requires_fields() -> None:
    """Verify required fields."""
    with pytest.raises(ValidationError):
        CheckRunCreate()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        CheckRunCreate(pull_request_id=uuid4())  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        CheckRunCreate(pull_request_id=uuid4(), external_id=123)  # type: ignore[call-arg]


@pytest.mark.unit
def test_check_run_create_rejects_empty_name() -> None:
    """Verify empty name is rejected."""
    with pytest.raises(ValidationError):
        CheckRunCreate(
            pull_request_id=uuid4(),
            external_id=123,
            head_sha="a" * 40,
            name="",
            status="queued",
        )


@pytest.mark.unit
def test_check_run_create_rejects_empty_head_sha() -> None:
    """Verify empty head_sha is rejected."""
    with pytest.raises(ValidationError):
        CheckRunCreate(
            pull_request_id=uuid4(),
            external_id=123,
            head_sha="",
            name="CI",
            status="queued",
        )


@pytest.mark.unit
def test_check_run_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = CheckRunUpdate(status="completed", conclusion="success")
    assert data.status == "completed"
    assert data.conclusion == "success"
    assert data.head_sha is None


@pytest.mark.unit
def test_check_run_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert CheckRunResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_check_run_service_model() -> None:
    """Verify service is configured with correct model."""
    service = CheckRunService()
    assert service.model is CheckRun
