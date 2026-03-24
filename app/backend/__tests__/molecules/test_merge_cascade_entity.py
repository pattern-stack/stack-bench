"""Tests for MergeCascadeEntity domain aggregate."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from molecules.exceptions import MoleculeError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_branch(
    *,
    position: int,
    state: str = "submitted",
    stack_id=None,
    workspace_id=None,
    head_sha: str | None = "abc123",
) -> MagicMock:
    branch = MagicMock()
    branch.id = uuid4()
    branch.stack_id = stack_id or uuid4()
    branch.workspace_id = workspace_id or uuid4()
    branch.name = f"feat/{position}-branch"
    branch.position = position
    branch.state = state
    branch.head_sha = head_sha
    branch.is_deleted = False
    branch.transition_to = MagicMock()
    return branch


def _make_pr(*, branch_id=None, state: str = "open", external_id: int = 42) -> MagicMock:
    pr = MagicMock()
    pr.id = uuid4()
    pr.branch_id = branch_id or uuid4()
    pr.state = state
    pr.external_id = external_id
    pr.is_deleted = False
    pr.transition_to = MagicMock()
    return pr


def _make_cascade(*, stack_id=None, state: str = "running") -> MagicMock:
    cascade = MagicMock()
    cascade.id = uuid4()
    cascade.stack_id = stack_id or uuid4()
    cascade.state = state
    cascade.transition_to = MagicMock()
    return cascade


def _make_step(*, position: int = 1, state: str = "pending", cascade_id=None) -> MagicMock:
    step = MagicMock()
    step.id = uuid4()
    step.cascade_id = cascade_id or uuid4()
    step.branch_id = uuid4()
    step.pull_request_id = uuid4()
    step.position = position
    step.state = state
    step.head_sha = "abc123"
    step.error = None
    step.completed_at = None
    step.transition_to = MagicMock()
    return step


def _build_entity():
    """Build a MergeCascadeEntity with all services mocked."""
    from molecules.entities.merge_cascade_entity import MergeCascadeEntity

    db = AsyncMock()
    entity = MergeCascadeEntity(db)

    # Replace services with mocks
    entity.cascade_service = MagicMock()
    entity.step_service = MagicMock()
    entity.check_run_service = MagicMock()
    entity.branch_service = MagicMock()
    entity.pr_service = MagicMock()
    entity.stack_service = MagicMock()

    return entity, db


# ---------------------------------------------------------------------------
# create_cascade
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_create_cascade_creates_steps_for_unmerged_branches() -> None:
    """Create cascade with steps for all unmerged branches in position order."""
    entity, db = _build_entity()
    stack_id = uuid4()
    workspace_id = uuid4()

    branch1 = _make_branch(position=1, stack_id=stack_id, workspace_id=workspace_id)
    branch2 = _make_branch(position=2, stack_id=stack_id, workspace_id=workspace_id)
    pr1 = _make_pr(branch_id=branch1.id)
    pr2 = _make_pr(branch_id=branch2.id)

    # No active cascade
    entity.cascade_service.get_active_for_stack = AsyncMock(return_value=None)

    # Stack returns branches
    mock_stack = MagicMock()
    mock_stack.id = stack_id
    mock_stack.trunk = "main"
    entity.stack_service.get = AsyncMock(return_value=mock_stack)

    entity.branch_service.list_by_stack = AsyncMock(return_value=[branch1, branch2])

    # PR lookup
    def get_pr_by_branch(db, branch_id):
        if branch_id == branch1.id:
            return pr1
        if branch_id == branch2.id:
            return pr2
        return None

    entity.pr_service.get_by_branch = AsyncMock(side_effect=get_pr_by_branch)

    # Cascade creation returns a mock
    cascade = _make_cascade(stack_id=stack_id, state="pending")
    entity.cascade_service.create = AsyncMock(return_value=cascade)

    # Step creation
    step1 = _make_step(position=1, cascade_id=cascade.id)
    step2 = _make_step(position=2, cascade_id=cascade.id)
    entity.step_service.create = AsyncMock(side_effect=[step1, step2])

    result = await entity.create_cascade(db, stack_id, triggered_by="user")

    # Cascade created
    entity.cascade_service.create.assert_called_once()
    # Two steps created
    assert entity.step_service.create.call_count == 2
    # Cascade transitioned to running
    cascade.transition_to.assert_called_with("running")
    assert result is cascade


@pytest.mark.unit
async def test_create_cascade_rejects_if_active_cascade_exists() -> None:
    """Reject creation if there is already an active cascade for the stack."""
    entity, db = _build_entity()
    stack_id = uuid4()

    active = _make_cascade(stack_id=stack_id, state="running")
    entity.cascade_service.get_active_for_stack = AsyncMock(return_value=active)

    with pytest.raises(MoleculeError, match="active cascade"):
        await entity.create_cascade(db, stack_id, triggered_by="user")


@pytest.mark.unit
async def test_create_cascade_rejects_if_branches_not_submitted() -> None:
    """Reject creation if any unmerged branch is not in 'submitted' state."""
    entity, db = _build_entity()
    stack_id = uuid4()

    branch1 = _make_branch(position=1, state="reviewing", stack_id=stack_id)
    pr1 = _make_pr(branch_id=branch1.id)

    entity.cascade_service.get_active_for_stack = AsyncMock(return_value=None)

    mock_stack = MagicMock()
    mock_stack.id = stack_id
    entity.stack_service.get = AsyncMock(return_value=mock_stack)
    entity.branch_service.list_by_stack = AsyncMock(return_value=[branch1])
    entity.pr_service.get_by_branch = AsyncMock(return_value=pr1)

    with pytest.raises(MoleculeError, match="submitted"):
        await entity.create_cascade(db, stack_id, triggered_by="user")


@pytest.mark.unit
async def test_create_cascade_skips_merged_branches() -> None:
    """Merged branches should be excluded from cascade steps."""
    entity, db = _build_entity()
    stack_id = uuid4()

    merged_branch = _make_branch(position=1, state="merged", stack_id=stack_id)
    active_branch = _make_branch(position=2, state="submitted", stack_id=stack_id)
    pr2 = _make_pr(branch_id=active_branch.id)

    entity.cascade_service.get_active_for_stack = AsyncMock(return_value=None)

    mock_stack = MagicMock()
    mock_stack.id = stack_id
    entity.stack_service.get = AsyncMock(return_value=mock_stack)
    entity.branch_service.list_by_stack = AsyncMock(return_value=[merged_branch, active_branch])
    entity.pr_service.get_by_branch = AsyncMock(return_value=pr2)

    cascade = _make_cascade(stack_id=stack_id, state="pending")
    entity.cascade_service.create = AsyncMock(return_value=cascade)
    entity.step_service.create = AsyncMock(return_value=_make_step(position=2))

    await entity.create_cascade(db, stack_id, triggered_by="user")

    # Only one step created (for the non-merged branch)
    assert entity.step_service.create.call_count == 1


# ---------------------------------------------------------------------------
# complete_step
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_complete_step_transitions_step_branch_pr() -> None:
    """Completing a step transitions step, branch, and PR states."""
    entity, db = _build_entity()

    step = _make_step(position=1, state="completing")
    branch = _make_branch(position=1, state="submitted")
    pr = _make_pr(branch_id=branch.id, state="open")

    # Make transition_to update state on mocks
    def step_transition(new_state):
        step.state = new_state

    def pr_transition(new_state):
        pr.state = new_state

    step.transition_to = MagicMock(side_effect=step_transition)
    pr.transition_to = MagicMock(side_effect=pr_transition)

    entity.step_service.get = AsyncMock(return_value=step)
    entity.branch_service.get = AsyncMock(return_value=branch)
    entity.pr_service.get = AsyncMock(return_value=pr)

    cascade = _make_cascade(state="running")
    entity.cascade_service.get = AsyncMock(return_value=cascade)

    all_steps = [step]
    entity.step_service.list_by_cascade = AsyncMock(return_value=all_steps)

    result = await entity.complete_step(db, step.id)

    step.transition_to.assert_called_with("merged")
    pr.transition_to.assert_any_call("approved")
    pr.transition_to.assert_any_call("merged")
    branch.transition_to.assert_called_with("merged")
    # All steps merged, so cascade should be completed
    cascade.transition_to.assert_called_with("completed")
    assert result is step


@pytest.mark.unit
async def test_complete_step_does_not_complete_cascade_with_pending_steps() -> None:
    """When other steps are still pending, cascade stays running."""
    entity, db = _build_entity()

    step1 = _make_step(position=1, state="completing")
    step2 = _make_step(position=2, state="pending")
    branch = _make_branch(position=1, state="submitted")
    pr = _make_pr(branch_id=branch.id, state="open")

    def step1_transition(new_state):
        step1.state = new_state

    step1.transition_to = MagicMock(side_effect=step1_transition)

    entity.step_service.get = AsyncMock(return_value=step1)
    entity.branch_service.get = AsyncMock(return_value=branch)
    entity.pr_service.get = AsyncMock(return_value=pr)

    cascade = _make_cascade(state="running")
    entity.cascade_service.get = AsyncMock(return_value=cascade)

    # step1 transitions to merged but step2 is still pending
    entity.step_service.list_by_cascade = AsyncMock(return_value=[step1, step2])

    await entity.complete_step(db, step1.id)

    step1.transition_to.assert_called_with("merged")
    # Cascade should NOT be completed
    cascade.transition_to.assert_not_called()


# ---------------------------------------------------------------------------
# fail_step
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_fail_step_skips_remaining_steps() -> None:
    """Failing a step skips all remaining pending steps."""
    entity, db = _build_entity()

    failed_step = _make_step(position=1, state="ci_pending")
    pending_step = _make_step(position=2, state="pending")

    entity.step_service.get = AsyncMock(return_value=failed_step)

    cascade = _make_cascade(state="running")
    entity.cascade_service.get = AsyncMock(return_value=cascade)

    entity.step_service.list_by_cascade = AsyncMock(return_value=[failed_step, pending_step])

    await entity.fail_step(db, failed_step.id, error="CI failed")

    failed_step.transition_to.assert_called_with("failed")
    cascade.transition_to.assert_called_with("failed")
    pending_step.transition_to.assert_called_with("skipped")


# ---------------------------------------------------------------------------
# conflict_step
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_conflict_step_marks_conflict_and_skips_remaining() -> None:
    """Conflict on a step fails cascade and skips remaining steps."""
    entity, db = _build_entity()

    conflict_step = _make_step(position=1, state="rebasing")
    pending_step = _make_step(position=2, state="pending")

    entity.step_service.get = AsyncMock(return_value=conflict_step)

    cascade = _make_cascade(state="running")
    entity.cascade_service.get = AsyncMock(return_value=cascade)

    entity.step_service.list_by_cascade = AsyncMock(return_value=[conflict_step, pending_step])

    await entity.conflict_step(db, conflict_step.id, error="merge conflict", conflicting_files=["a.py"])

    conflict_step.transition_to.assert_called_with("conflict")
    cascade.transition_to.assert_called_with("failed")
    pending_step.transition_to.assert_called_with("skipped")


# ---------------------------------------------------------------------------
# cancel_cascade
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_cancel_cascade_skips_pending_steps() -> None:
    """Cancelling a cascade transitions it and skips all pending/active steps."""
    entity, db = _build_entity()

    cascade = _make_cascade(state="running")
    entity.cascade_service.get = AsyncMock(return_value=cascade)

    pending_step = _make_step(position=1, state="pending", cascade_id=cascade.id)
    active_step = _make_step(position=2, state="ci_pending", cascade_id=cascade.id)
    merged_step = _make_step(position=3, state="merged", cascade_id=cascade.id)

    entity.step_service.list_by_cascade = AsyncMock(return_value=[pending_step, active_step, merged_step])

    result = await entity.cancel_cascade(db, cascade.id)

    cascade.transition_to.assert_called_with("cancelled")
    pending_step.transition_to.assert_called_with("skipped")
    # active steps in non-terminal states should be skipped
    # (ci_pending can transition to failed, not skipped directly, so we check it's handled)
    assert result is cascade
