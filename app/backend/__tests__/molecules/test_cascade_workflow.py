"""Tests for CascadeWorkflow orchestration logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_branch(*, position: int = 1, head_sha: str = "abc123", workspace_id=None) -> MagicMock:
    branch = MagicMock()
    branch.id = uuid4()
    branch.name = f"feat/{position}-branch"
    branch.position = position
    branch.head_sha = head_sha
    branch.workspace_id = workspace_id or uuid4()
    branch.stack_id = uuid4()
    branch.state = "submitted"
    return branch


def _make_pr(*, external_id: int = 42, state: str = "open", base_ref: str | None = None) -> MagicMock:
    pr = MagicMock()
    pr.id = uuid4()
    pr.external_id = external_id
    pr.state = state
    pr.base_ref = base_ref
    return pr


def _make_step(*, position: int = 1, state: str = "pending") -> MagicMock:
    step = MagicMock()
    step.id = uuid4()
    step.cascade_id = uuid4()
    step.branch_id = uuid4()
    step.pull_request_id = uuid4()
    step.position = position
    step.state = state
    step.head_sha = "abc123"
    step.check_run_external_id = None
    step.error = None
    step.started_at = None
    step.completed_at = None
    step.transition_to = MagicMock()
    return step


def _make_cascade(*, state: str = "running") -> MagicMock:
    cascade = MagicMock()
    cascade.id = uuid4()
    cascade.stack_id = uuid4()
    cascade.state = state
    cascade.transition_to = MagicMock()
    return cascade


def _make_workspace(*, repo_url: str = "https://github.com/org/repo") -> MagicMock:
    ws = MagicMock()
    ws.id = uuid4()
    ws.repo_url = repo_url
    return ws


def _make_stack(*, trunk: str = "main") -> MagicMock:
    stack = MagicMock()
    stack.id = uuid4()
    stack.trunk = trunk
    return stack


def _build_workflow():
    """Build a CascadeWorkflow with all dependencies mocked."""
    from molecules.workflows.cascade_workflow import CascadeWorkflow

    entity = MagicMock()
    # Make all service method calls return AsyncMock so they're awaitable
    entity.branch_service.get = AsyncMock()
    entity.pr_service.get = AsyncMock()
    entity.pr_service.update = AsyncMock()
    entity.stack_service.get = AsyncMock()
    entity.cascade_service.get = AsyncMock()
    entity.step_service.get = AsyncMock()
    entity.step_service.update = AsyncMock()
    entity.step_service.get_pending_step = AsyncMock()
    entity.step_service.list_by_cascade = AsyncMock()
    entity.check_run_service.create = AsyncMock()
    entity.check_run_service.update = AsyncMock()
    entity.complete_step = AsyncMock()
    entity.fail_step = AsyncMock()
    entity.conflict_step = AsyncMock()

    github = AsyncMock()
    clone_manager = MagicMock()

    workflow = CascadeWorkflow(entity=entity, github=github, clone_manager=clone_manager)
    return workflow, entity, github, clone_manager


# ---------------------------------------------------------------------------
# process_step: happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_process_step_happy_path() -> None:
    """Process step: retarget, rebase, create check run."""
    workflow, entity, github, clone_manager = _build_workflow()

    step = _make_step(position=1, state="pending")
    branch = _make_branch(position=1, head_sha="old_sha")
    pr = _make_pr(external_id=42)
    stack = _make_stack(trunk="main")
    workspace = _make_workspace()

    # Entity lookups
    entity.branch_service.get.return_value = branch
    entity.pr_service.get.return_value = pr
    entity.pr_service.update.return_value = pr
    entity.stack_service.get.return_value = stack
    cascade_mock = _make_cascade()
    cascade_mock.stack_id = stack.id
    entity.cascade_service.get.return_value = cascade_mock

    # GitHub retarget
    github.retarget_pr = AsyncMock(return_value={})

    # Rebase via clone (mock the context manager)
    mock_ctx = MagicMock()
    mock_ctx.path = MagicMock()

    mock_git = AsyncMock()
    mock_git.checkout = AsyncMock(return_value=MagicMock(success=True))
    mock_git.rebase = AsyncMock(return_value=MagicMock(success=True, has_conflicts=False))
    mock_git.push = AsyncMock(return_value=MagicMock(success=True))
    mock_git.get_head_sha = AsyncMock(return_value="new_sha_after_rebase")

    # We patch the clone manager and GitOperations
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_clone(*args, **kwargs):
        yield mock_ctx

    clone_manager.clone = mock_clone

    with patch("molecules.workflows.cascade_workflow.GitOperations", return_value=mock_git):
        # GitHub create check run
        github.create_check_run.return_value = {"id": 999}

        # CheckRun service
        entity.check_run_service.create.return_value = MagicMock()

        await workflow.process_step(db=AsyncMock(), cascade_id=step.cascade_id, step=step, workspace=workspace)

    # Retarget was called
    github.retarget_pr.assert_called_once_with("org", "repo", 42, "main")

    # Step transitioned through states
    step.transition_to.assert_any_call("retargeting")
    step.transition_to.assert_any_call("rebasing")
    step.transition_to.assert_any_call("ci_pending")

    # Check run was created
    github.create_check_run.assert_called_once()


# ---------------------------------------------------------------------------
# process_step: conflict
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_process_step_conflict_calls_entity_conflict() -> None:
    """On rebase conflict, entity.conflict_step is called."""
    workflow, entity, github, clone_manager = _build_workflow()

    step = _make_step(position=1, state="pending")
    branch = _make_branch(position=1)
    pr = _make_pr(external_id=42)
    stack = _make_stack(trunk="main")
    workspace = _make_workspace()

    entity.branch_service.get.return_value = branch
    entity.pr_service.get.return_value = pr
    entity.pr_service.update.return_value = pr
    cascade_mock = _make_cascade()
    cascade_mock.stack_id = stack.id
    entity.stack_service.get.return_value = stack
    entity.cascade_service.get.return_value = cascade_mock

    github.retarget_pr.return_value = {}

    mock_ctx = MagicMock()
    mock_git = AsyncMock()
    mock_git.checkout = AsyncMock(return_value=MagicMock(success=True))

    # Fetch succeeds
    mock_git._run = AsyncMock(return_value=("", "", 0))

    # Rebase fails with conflict
    mock_git.rebase = AsyncMock(
        return_value=MagicMock(success=False, has_conflicts=True, conflicting_files=["file.py"], error="conflict")
    )

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_clone(*args, **kwargs):
        yield mock_ctx

    clone_manager.clone = mock_clone

    entity.conflict_step.return_value = step

    with patch("molecules.workflows.cascade_workflow.GitOperations", return_value=mock_git):
        await workflow.process_step(db=AsyncMock(), cascade_id=step.cascade_id, step=step, workspace=workspace)

    entity.conflict_step.assert_called_once()


# ---------------------------------------------------------------------------
# evaluate_step: CI green
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_evaluate_step_all_ci_green_merges_pr() -> None:
    """When all external CI passes, check run completed and PR merged."""
    workflow, entity, github, clone_manager = _build_workflow()

    step = _make_step(position=1, state="ci_pending")
    step.head_sha = "sha123"
    step.check_run_external_id = 999
    workspace = _make_workspace()

    # External check suites: all passed (excluding ours)
    github.get_check_suites = AsyncMock(
        return_value=[
            {"app": {"name": "GitHub Actions"}, "status": "completed", "conclusion": "success"},
            {"app": {"name": "Stack Bench"}, "status": "in_progress", "conclusion": None},
        ]
    )

    # GitHub calls
    github.update_check_run.return_value = {}
    github.merge_pr.return_value = {"merged": True, "sha": "merge_sha"}

    # Entity lookups
    pr = _make_pr(external_id=42, state="open")
    entity.pr_service.get.return_value = pr
    entity.complete_step.return_value = step

    cascade = _make_cascade()
    entity.cascade_service.get.return_value = cascade

    await workflow.evaluate_step(db=AsyncMock(), step=step, workspace=workspace)

    # Our check run was completed with success
    github.update_check_run.assert_called_once()
    call_args = github.update_check_run.call_args
    assert call_args[1].get("conclusion") == "success" or call_args[0][4] == "success" or "success" in str(call_args)

    # PR was merged
    github.merge_pr.assert_called_once()


# ---------------------------------------------------------------------------
# evaluate_step: CI failed
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_evaluate_step_ci_failed_fails_step() -> None:
    """When external CI fails, step is failed."""
    workflow, entity, github, clone_manager = _build_workflow()

    step = _make_step(position=1, state="ci_pending")
    step.head_sha = "sha123"
    step.check_run_external_id = 999
    workspace = _make_workspace()

    github.get_check_suites.return_value = [
        {"app": {"name": "GitHub Actions"}, "status": "completed", "conclusion": "failure"},
    ]

    github.update_check_run.return_value = {}
    entity.fail_step.return_value = step

    cascade = _make_cascade()
    entity.cascade_service.get.return_value = cascade

    await workflow.evaluate_step(db=AsyncMock(), step=step, workspace=workspace)

    entity.fail_step.assert_called_once()


# ---------------------------------------------------------------------------
# advance_cascade: remaining steps
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_advance_cascade_processes_next_step() -> None:
    """When there are remaining steps, advance processes the next one."""
    workflow, entity, github, clone_manager = _build_workflow()

    cascade_id = uuid4()
    next_step = _make_step(position=2, state="pending")
    workspace = _make_workspace()

    entity.step_service.get_pending_step.return_value = next_step
    entity.cascade_service.get.return_value = _make_cascade()

    # Mock process_step to avoid full execution
    workflow.process_step = AsyncMock(return_value=next_step)

    result = await workflow.advance_cascade(db=AsyncMock(), cascade_id=cascade_id, workspace=workspace)

    workflow.process_step.assert_called_once()
    assert result is next_step


# ---------------------------------------------------------------------------
# advance_cascade: no remaining steps
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_advance_cascade_completes_when_no_remaining() -> None:
    """When no pending steps remain, cascade is completed."""
    workflow, entity, github, clone_manager = _build_workflow()

    cascade_id = uuid4()
    cascade = _make_cascade(state="running")
    workspace = _make_workspace()

    entity.step_service.get_pending_step.return_value = None
    entity.cascade_service.get.return_value = cascade

    result = await workflow.advance_cascade(db=AsyncMock(), cascade_id=cascade_id, workspace=workspace)

    cascade.transition_to.assert_called_with("completed")
    assert result is None
