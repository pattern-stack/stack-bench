import pytest
from pydantic import ValidationError
from uuid import uuid4

from features.pull_requests.models import PullRequest
from features.pull_requests.schemas.input import PullRequestCreate, PullRequestUpdate
from features.pull_requests.schemas.output import PullRequestResponse
from features.pull_requests.service import PullRequestService


@pytest.mark.unit
def test_pull_request_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(PullRequest, "branch_id")
    assert hasattr(PullRequest, "external_id")
    assert hasattr(PullRequest, "external_url")
    assert hasattr(PullRequest, "title")
    assert hasattr(PullRequest, "description")
    assert hasattr(PullRequest, "review_notes")
    assert hasattr(PullRequest, "state")


@pytest.mark.unit
def test_pull_request_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert PullRequest.Pattern.entity == "pull_request"
    assert PullRequest.Pattern.reference_prefix == "PR"
    assert PullRequest.Pattern.initial_state == "draft"
    assert "draft" in PullRequest.Pattern.states
    assert "open" in PullRequest.Pattern.states
    assert "approved" in PullRequest.Pattern.states
    assert "merged" in PullRequest.Pattern.states
    assert "closed" in PullRequest.Pattern.states


@pytest.mark.unit
def test_pull_request_state_machine() -> None:
    """Verify state machine transitions."""
    pr = PullRequest()
    assert pr.state == "draft"
    assert pr.can_transition_to("open")
    pr.transition_to("open")
    assert pr.state == "open"
    assert pr.can_transition_to("approved")
    assert pr.can_transition_to("closed")


@pytest.mark.unit
def test_pull_request_invalid_transition() -> None:
    """Verify draft cannot transition to approved, merged, or closed."""
    pr = PullRequest()
    assert not pr.can_transition_to("approved")
    assert not pr.can_transition_to("merged")
    assert not pr.can_transition_to("closed")


@pytest.mark.unit
def test_pull_request_full_lifecycle() -> None:
    """Verify full lifecycle: draft -> open -> approved -> merged."""
    pr = PullRequest()
    assert pr.state == "draft"
    pr.transition_to("open")
    assert pr.state == "open"
    pr.transition_to("approved")
    assert pr.state == "approved"
    pr.transition_to("merged")
    assert pr.state == "merged"
    assert pr.get_allowed_transitions() == []


@pytest.mark.unit
def test_pull_request_closed_path() -> None:
    """Verify draft -> open -> closed, closed can reopen to open."""
    pr = PullRequest()
    pr.transition_to("open")
    pr.transition_to("closed")
    assert pr.state == "closed"
    assert pr.can_transition_to("open")


@pytest.mark.unit
def test_pull_request_reopen() -> None:
    """Verify draft -> open -> closed -> open transition succeeds."""
    pr = PullRequest()
    pr.transition_to("open")
    pr.transition_to("closed")
    pr.transition_to("open")
    assert pr.state == "open"


@pytest.mark.unit
def test_pull_request_approved_to_closed() -> None:
    """Verify draft -> open -> approved -> closed is allowed."""
    pr = PullRequest()
    pr.transition_to("open")
    pr.transition_to("approved")
    pr.transition_to("closed")
    assert pr.state == "closed"


@pytest.mark.unit
def test_pull_request_create_schema() -> None:
    """Verify create schema with minimal data."""
    data = PullRequestCreate(branch_id=uuid4(), title="Add feature X")
    assert data.external_id is None
    assert data.description is None
    assert data.review_notes is None


@pytest.mark.unit
def test_pull_request_create_schema_full() -> None:
    """Verify create schema with all fields."""
    data = PullRequestCreate(
        branch_id=uuid4(),
        title="Add feature X",
        description="Implements the X feature",
        review_notes="Check error handling",
        external_id=42,
        external_url="https://github.com/org/repo/pull/42",
    )
    assert data.external_id == 42
    assert data.external_url == "https://github.com/org/repo/pull/42"


@pytest.mark.unit
def test_pull_request_create_requires_fields() -> None:
    """Verify required fields."""
    with pytest.raises(ValidationError):
        PullRequestCreate()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        PullRequestCreate(branch_id=uuid4())  # type: ignore[call-arg]


@pytest.mark.unit
def test_pull_request_create_rejects_empty_title() -> None:
    """Verify empty title is rejected."""
    with pytest.raises(ValidationError):
        PullRequestCreate(branch_id=uuid4(), title="")


@pytest.mark.unit
def test_pull_request_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = PullRequestUpdate(title="Updated title")
    assert data.title == "Updated title"
    assert data.description is None
    assert data.review_notes is None


@pytest.mark.unit
def test_pull_request_update_review_notes() -> None:
    """Verify update schema accepts review_notes."""
    data = PullRequestUpdate(review_notes="## Feedback\n- Fix error handling")
    assert data.review_notes == "## Feedback\n- Fix error handling"


@pytest.mark.unit
def test_pull_request_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert PullRequestResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_pull_request_service_model() -> None:
    """Verify service is configured with correct model."""
    service = PullRequestService()
    assert service.model is PullRequest
