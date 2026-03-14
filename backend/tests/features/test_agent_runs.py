import uuid

import pytest
from pydantic import ValidationError

from features.agent_runs.models import AgentRun
from features.agent_runs.schemas.input import AgentRunCreate, AgentRunUpdate
from features.agent_runs.schemas.output import AgentRunResponse
from features.agent_runs.service import AgentRunService


@pytest.mark.unit
def test_agent_run_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(AgentRun, "job_id")
    assert hasattr(AgentRun, "phase")
    assert hasattr(AgentRun, "runner_type")
    assert hasattr(AgentRun, "model_used")
    assert hasattr(AgentRun, "input_tokens")
    assert hasattr(AgentRun, "output_tokens")
    assert hasattr(AgentRun, "artifact")
    assert hasattr(AgentRun, "error_message")
    assert hasattr(AgentRun, "duration_ms")
    assert hasattr(AgentRun, "attempt")
    assert hasattr(AgentRun, "state")


@pytest.mark.unit
def test_agent_run_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert AgentRun.Pattern.entity == "agent_run"
    assert AgentRun.Pattern.reference_prefix == "RUN"
    assert AgentRun.Pattern.initial_state == "pending"
    assert "pending" in AgentRun.Pattern.states
    assert "running" in AgentRun.Pattern.states["pending"]


@pytest.mark.unit
def test_agent_run_initial_state() -> None:
    """Verify agent run starts in pending state."""
    run = AgentRun()
    assert run.state == "pending"


@pytest.mark.unit
def test_agent_run_state_machine_happy_path() -> None:
    """Verify happy path: pending -> running -> complete."""
    run = AgentRun()
    assert run.can_transition_to("running")
    run.transition_to("running")
    assert run.state == "running"
    assert run.can_transition_to("complete")
    run.transition_to("complete")
    assert run.state == "complete"
    assert run.get_allowed_transitions() == []


@pytest.mark.unit
def test_agent_run_failure_path() -> None:
    """Verify failure path: pending -> running -> failed."""
    run = AgentRun()
    run.transition_to("running")
    run.transition_to("failed")
    assert run.state == "failed"
    assert run.get_allowed_transitions() == []


@pytest.mark.unit
def test_agent_run_cannot_skip_states() -> None:
    """Verify invalid transitions are rejected."""
    run = AgentRun()
    assert not run.can_transition_to("complete")
    assert not run.can_transition_to("failed")


@pytest.mark.unit
def test_agent_run_cannot_go_backwards() -> None:
    """Verify completed run cannot transition back."""
    run = AgentRun()
    run.transition_to("running")
    run.transition_to("complete")
    assert not run.can_transition_to("running")
    assert not run.can_transition_to("pending")


@pytest.mark.unit
def test_agent_run_create_schema_minimal() -> None:
    """Verify create schema with minimal data."""
    job_id = uuid.uuid4()
    data = AgentRunCreate(job_id=job_id, phase="planning", runner_type="architect")
    assert data.job_id == job_id
    assert data.phase == "planning"
    assert data.runner_type == "architect"
    assert data.model_used is None
    assert data.attempt == 1


@pytest.mark.unit
def test_agent_run_create_schema_full() -> None:
    """Verify create schema with all fields."""
    job_id = uuid.uuid4()
    data = AgentRunCreate(
        job_id=job_id,
        phase="implementation",
        runner_type="builder",
        model_used="claude-opus-4-20250514",
        attempt=2,
    )
    assert data.model_used == "claude-opus-4-20250514"
    assert data.attempt == 2


@pytest.mark.unit
def test_agent_run_create_requires_fields() -> None:
    """Verify required fields are enforced."""
    with pytest.raises(ValidationError):
        AgentRunCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_agent_run_create_rejects_empty_phase() -> None:
    """Verify empty phase is rejected."""
    with pytest.raises(ValidationError):
        AgentRunCreate(job_id=uuid.uuid4(), phase="", runner_type="builder")


@pytest.mark.unit
def test_agent_run_create_rejects_empty_runner_type() -> None:
    """Verify empty runner_type is rejected."""
    with pytest.raises(ValidationError):
        AgentRunCreate(job_id=uuid.uuid4(), phase="planning", runner_type="")


@pytest.mark.unit
def test_agent_run_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = AgentRunUpdate(input_tokens=500, output_tokens=1200)
    assert data.input_tokens == 500
    assert data.output_tokens == 1200
    assert data.model_used is None
    assert data.artifact is None
    assert data.error_message is None
    assert data.duration_ms is None


@pytest.mark.unit
def test_agent_run_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert AgentRunResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_agent_run_service_model() -> None:
    """Verify service is configured with correct model."""
    service = AgentRunService()
    assert service.model is AgentRun
