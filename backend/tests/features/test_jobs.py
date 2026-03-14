import pytest
from pydantic import ValidationError

from features.jobs.models import Job
from features.jobs.schemas.input import JobCreate, JobUpdate
from features.jobs.schemas.output import JobResponse
from features.jobs.service import JobService


@pytest.mark.unit
def test_job_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(Job, "repo_url")
    assert hasattr(Job, "repo_branch")
    assert hasattr(Job, "issue_number")
    assert hasattr(Job, "issue_title")
    assert hasattr(Job, "issue_body")
    assert hasattr(Job, "current_phase")
    assert hasattr(Job, "input_text")
    assert hasattr(Job, "error_message")
    assert hasattr(Job, "artifacts")
    assert hasattr(Job, "gate_decisions")
    assert hasattr(Job, "job_record_id")
    assert hasattr(Job, "state")


@pytest.mark.unit
def test_job_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert Job.Pattern.entity == "job"
    assert Job.Pattern.reference_prefix == "JOB"
    assert Job.Pattern.initial_state == "queued"
    assert "queued" in Job.Pattern.states
    assert "running" in Job.Pattern.states["queued"]


@pytest.mark.unit
def test_job_initial_state() -> None:
    """Verify job starts in queued state."""
    job = Job()
    assert job.state == "queued"


@pytest.mark.unit
def test_job_state_machine_happy_path() -> None:
    """Verify happy path: queued -> running -> complete."""
    job = Job()
    assert job.can_transition_to("running")
    job.transition_to("running")
    assert job.state == "running"
    assert job.can_transition_to("complete")
    job.transition_to("complete")
    assert job.state == "complete"
    assert job.get_allowed_transitions() == []


@pytest.mark.unit
def test_job_state_machine_gated() -> None:
    """Verify gated flow: running -> gated -> running -> complete."""
    job = Job()
    job.transition_to("running")
    job.transition_to("gated")
    assert job.state == "gated"
    assert job.can_transition_to("running")
    job.transition_to("running")
    assert job.state == "running"


@pytest.mark.unit
def test_job_cannot_skip_states() -> None:
    """Verify invalid transitions are rejected."""
    job = Job()
    assert not job.can_transition_to("complete")
    assert not job.can_transition_to("gated")
    assert not job.can_transition_to("failed")


@pytest.mark.unit
def test_job_cancellation_from_queued() -> None:
    """Verify cancellation from queued state."""
    job = Job()
    assert job.can_transition_to("cancelled")
    job.transition_to("cancelled")
    assert job.state == "cancelled"
    assert job.get_allowed_transitions() == []


@pytest.mark.unit
def test_job_cancellation_from_running() -> None:
    """Verify cancellation from running state."""
    job = Job()
    job.transition_to("running")
    assert job.can_transition_to("cancelled")


@pytest.mark.unit
def test_job_cancellation_from_gated() -> None:
    """Verify cancellation from gated state."""
    job = Job()
    job.transition_to("running")
    job.transition_to("gated")
    assert job.can_transition_to("cancelled")


@pytest.mark.unit
def test_job_failure_path() -> None:
    """Verify failure path: queued -> running -> failed."""
    job = Job()
    job.transition_to("running")
    job.transition_to("failed")
    assert job.state == "failed"
    assert job.get_allowed_transitions() == []


@pytest.mark.unit
def test_job_create_schema_minimal() -> None:
    """Verify create schema with minimal data."""
    data = JobCreate(repo_url="https://github.com/org/repo")
    assert data.repo_url == "https://github.com/org/repo"
    assert data.repo_branch == "main"
    assert data.issue_number is None
    assert data.issue_title is None
    assert data.issue_body is None
    assert data.input_text is None


@pytest.mark.unit
def test_job_create_schema_full() -> None:
    """Verify create schema with all fields."""
    data = JobCreate(
        repo_url="https://github.com/org/repo",
        repo_branch="feature/test",
        issue_number=42,
        issue_title="Fix the thing",
        issue_body="Detailed description",
        input_text="Additional context",
    )
    assert data.repo_branch == "feature/test"
    assert data.issue_number == 42


@pytest.mark.unit
def test_job_create_requires_repo_url() -> None:
    """Verify repo_url is required."""
    with pytest.raises(ValidationError):
        JobCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_job_create_rejects_empty_repo_url() -> None:
    """Verify empty repo_url is rejected."""
    with pytest.raises(ValidationError):
        JobCreate(repo_url="")


@pytest.mark.unit
def test_job_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = JobUpdate(current_phase="planning")
    assert data.current_phase == "planning"
    assert data.error_message is None
    assert data.artifacts is None
    assert data.gate_decisions is None


@pytest.mark.unit
def test_job_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert JobResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_job_service_model() -> None:
    """Verify service is configured with correct model."""
    service = JobService()
    assert service.model is Job
