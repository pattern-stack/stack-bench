import pytest
from pydantic import ValidationError
from uuid import uuid4

from features.stacks.models import Stack
from features.stacks.schemas.input import StackCreate, StackUpdate
from features.stacks.schemas.output import StackResponse
from features.stacks.service import StackService


@pytest.mark.unit
def test_stack_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(Stack, "project_id")
    assert hasattr(Stack, "name")
    assert hasattr(Stack, "base_branch_id")
    assert hasattr(Stack, "trunk")
    assert hasattr(Stack, "state")


@pytest.mark.unit
def test_stack_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert Stack.Pattern.entity == "stack"
    assert Stack.Pattern.reference_prefix == "STK"
    assert Stack.Pattern.initial_state == "draft"
    assert "draft" in Stack.Pattern.states
    assert "active" in Stack.Pattern.states
    assert "submitted" in Stack.Pattern.states
    assert "merged" in Stack.Pattern.states
    assert "closed" in Stack.Pattern.states


@pytest.mark.unit
def test_stack_state_machine() -> None:
    """Verify state machine transitions."""
    stack = Stack()
    assert stack.state == "draft"
    assert stack.can_transition_to("active")
    stack.transition_to("active")
    assert stack.state == "active"
    assert stack.can_transition_to("submitted")
    assert stack.can_transition_to("closed")


@pytest.mark.unit
def test_stack_invalid_transition() -> None:
    """Verify draft cannot transition to submitted, merged, or closed directly."""
    stack = Stack()
    assert not stack.can_transition_to("submitted")
    assert not stack.can_transition_to("merged")
    assert not stack.can_transition_to("closed")


@pytest.mark.unit
def test_stack_full_lifecycle() -> None:
    """Verify full lifecycle: draft -> active -> submitted -> merged."""
    stack = Stack()
    assert stack.state == "draft"
    stack.transition_to("active")
    assert stack.state == "active"
    stack.transition_to("submitted")
    assert stack.state == "submitted"
    stack.transition_to("merged")
    assert stack.state == "merged"
    assert stack.get_allowed_transitions() == []


@pytest.mark.unit
def test_stack_closed_path() -> None:
    """Verify draft -> active -> closed, closed is terminal."""
    stack = Stack()
    stack.transition_to("active")
    stack.transition_to("closed")
    assert stack.state == "closed"
    assert stack.get_allowed_transitions() == []


@pytest.mark.unit
def test_stack_submitted_to_closed() -> None:
    """Verify draft -> active -> submitted -> closed, closed is terminal."""
    stack = Stack()
    stack.transition_to("active")
    stack.transition_to("submitted")
    stack.transition_to("closed")
    assert stack.state == "closed"
    assert stack.get_allowed_transitions() == []


@pytest.mark.unit
def test_stack_create_schema() -> None:
    """Verify create schema with minimal data."""
    data = StackCreate(project_id=uuid4(), name="my-stack")
    assert data.trunk == "main"
    assert data.base_branch_id is None


@pytest.mark.unit
def test_stack_create_schema_full() -> None:
    """Verify create schema with all fields."""
    branch_id = uuid4()
    data = StackCreate(
        project_id=uuid4(),
        name="my-stack",
        base_branch_id=branch_id,
        trunk="develop",
    )
    assert data.base_branch_id == branch_id
    assert data.trunk == "develop"


@pytest.mark.unit
def test_stack_create_requires_fields() -> None:
    """Verify required fields."""
    with pytest.raises(ValidationError):
        StackCreate()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        StackCreate(project_id=uuid4())  # type: ignore[call-arg]


@pytest.mark.unit
def test_stack_create_rejects_empty_name() -> None:
    """Verify empty name is rejected."""
    with pytest.raises(ValidationError):
        StackCreate(project_id=uuid4(), name="")


@pytest.mark.unit
def test_stack_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = StackUpdate(name="new-name")
    assert data.name == "new-name"
    assert data.trunk is None
    assert data.base_branch_id is None


@pytest.mark.unit
def test_stack_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert StackResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_stack_service_model() -> None:
    """Verify service is configured with correct model."""
    service = StackService()
    assert service.model is Stack
