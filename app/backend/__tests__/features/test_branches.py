from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.branches.models import Branch
from features.branches.schemas.input import BranchCreate, BranchUpdate
from features.branches.schemas.output import BranchResponse
from features.branches.service import BranchService


@pytest.mark.unit
def test_branch_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(Branch, "stack_id")
    assert hasattr(Branch, "workspace_id")
    assert hasattr(Branch, "name")
    assert hasattr(Branch, "position")
    assert hasattr(Branch, "head_sha")
    assert hasattr(Branch, "state")


@pytest.mark.unit
def test_branch_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert Branch.Pattern.entity == "branch"
    assert Branch.Pattern.reference_prefix == "BR"
    assert Branch.Pattern.initial_state == "created"
    assert "created" in Branch.Pattern.states
    assert "pushed" in Branch.Pattern.states
    assert "reviewing" in Branch.Pattern.states
    assert "ready" in Branch.Pattern.states
    assert "submitted" in Branch.Pattern.states
    assert "merged" in Branch.Pattern.states


@pytest.mark.unit
def test_branch_state_machine() -> None:
    """Verify state machine transitions."""
    branch = Branch()
    assert branch.state == "created"
    assert branch.can_transition_to("pushed")
    branch.transition_to("pushed")
    assert branch.state == "pushed"
    assert branch.can_transition_to("reviewing")


@pytest.mark.unit
def test_branch_invalid_transition() -> None:
    """Verify created cannot transition to reviewing, ready, submitted, or merged."""
    branch = Branch()
    assert not branch.can_transition_to("reviewing")
    assert not branch.can_transition_to("ready")
    assert not branch.can_transition_to("submitted")
    assert not branch.can_transition_to("merged")


@pytest.mark.unit
def test_branch_full_lifecycle() -> None:
    """Verify full lifecycle: created -> pushed -> reviewing -> ready -> submitted -> merged."""
    branch = Branch()
    assert branch.state == "created"
    branch.transition_to("pushed")
    assert branch.state == "pushed"
    branch.transition_to("reviewing")
    assert branch.state == "reviewing"
    branch.transition_to("ready")
    assert branch.state == "ready"
    branch.transition_to("submitted")
    assert branch.state == "submitted"
    branch.transition_to("merged")
    assert branch.state == "merged"
    assert branch.get_allowed_transitions() == []


@pytest.mark.unit
def test_branch_direct_merge_from_pushed() -> None:
    """Verify pushed branches can transition directly to merged."""
    branch = Branch()
    branch.transition_to("pushed")
    assert branch.can_transition_to("merged")
    branch.transition_to("merged")
    assert branch.state == "merged"


@pytest.mark.unit
def test_branch_direct_merge_from_reviewing() -> None:
    """Verify reviewing branches can transition directly to merged."""
    branch = Branch()
    branch.transition_to("pushed")
    branch.transition_to("reviewing")
    assert branch.can_transition_to("merged")
    branch.transition_to("merged")
    assert branch.state == "merged"


@pytest.mark.unit
def test_branch_direct_merge_from_ready() -> None:
    """Verify ready branches can transition directly to merged."""
    branch = Branch()
    branch.transition_to("pushed")
    branch.transition_to("reviewing")
    branch.transition_to("ready")
    assert branch.can_transition_to("merged")
    branch.transition_to("merged")
    assert branch.state == "merged"


@pytest.mark.unit
def test_branch_create_schema() -> None:
    """Verify create schema with minimal data."""
    data = BranchCreate(
        stack_id=uuid4(),
        workspace_id=uuid4(),
        name="user/stack/1-feat",
        position=1,
    )
    assert data.head_sha is None


@pytest.mark.unit
def test_branch_create_schema_with_sha() -> None:
    """Verify create schema with head_sha."""
    data = BranchCreate(
        stack_id=uuid4(),
        workspace_id=uuid4(),
        name="user/stack/1-feat",
        position=1,
        head_sha="a" * 40,
    )
    assert data.head_sha == "a" * 40


@pytest.mark.unit
def test_branch_create_requires_fields() -> None:
    """Verify required fields."""
    with pytest.raises(ValidationError):
        BranchCreate()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BranchCreate(stack_id=uuid4())  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BranchCreate(stack_id=uuid4(), workspace_id=uuid4())  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BranchCreate(stack_id=uuid4(), workspace_id=uuid4(), name="feat")  # type: ignore[call-arg]


@pytest.mark.unit
def test_branch_create_rejects_zero_position() -> None:
    """Verify position=0 is rejected."""
    with pytest.raises(ValidationError):
        BranchCreate(
            stack_id=uuid4(),
            workspace_id=uuid4(),
            name="user/stack/1-feat",
            position=0,
        )


@pytest.mark.unit
def test_branch_create_rejects_empty_name() -> None:
    """Verify empty name is rejected."""
    with pytest.raises(ValidationError):
        BranchCreate(
            stack_id=uuid4(),
            workspace_id=uuid4(),
            name="",
            position=1,
        )


@pytest.mark.unit
def test_branch_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = BranchUpdate(head_sha="b" * 40)
    assert data.head_sha == "b" * 40
    assert data.name is None
    assert data.position is None
    assert data.workspace_id is None


@pytest.mark.unit
def test_branch_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert BranchResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_branch_service_model() -> None:
    """Verify service is configured with correct model."""
    service = BranchService()
    assert service.model is Branch
