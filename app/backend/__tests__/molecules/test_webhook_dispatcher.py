"""Tests for WebhookDispatcher -- routes GitHub webhook events to domain handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_step(*, state: str = "ci_pending", head_sha: str = "abc123") -> MagicMock:
    step = MagicMock()
    step.id = uuid4()
    step.cascade_id = uuid4()
    step.branch_id = uuid4()
    step.pull_request_id = uuid4()
    step.state = state
    step.head_sha = head_sha
    step.check_run_external_id = 999
    return step


def _make_pr(*, external_id: int = 42, state: str = "open") -> MagicMock:
    pr = MagicMock()
    pr.id = uuid4()
    pr.external_id = external_id
    pr.state = state
    return pr


def _make_workspace(*, repo_url: str = "https://github.com/org/repo") -> MagicMock:
    ws = MagicMock()
    ws.id = uuid4()
    ws.repo_url = repo_url
    return ws


def _make_branch(*, workspace_id=None) -> MagicMock:
    branch = MagicMock()
    branch.id = uuid4()
    branch.workspace_id = workspace_id or uuid4()
    return branch


def _build_dispatcher():
    """Build a WebhookDispatcher with all dependencies mocked."""
    from molecules.services.webhook_dispatcher import WebhookDispatcher

    cascade_workflow = AsyncMock()
    cascade_step_service = AsyncMock()
    pull_request_service = AsyncMock()
    workspace_service = AsyncMock()
    branch_service = AsyncMock()
    db = AsyncMock()

    dispatcher = WebhookDispatcher(
        cascade_workflow=cascade_workflow,
        cascade_step_service=cascade_step_service,
        pull_request_service=pull_request_service,
        workspace_service=workspace_service,
        branch_service=branch_service,
        db=db,
    )
    return (
        dispatcher,
        cascade_workflow,
        cascade_step_service,
        pull_request_service,
        workspace_service,
        branch_service,
        db,
    )


# ---------------------------------------------------------------------------
# _handle_check_suite_completed: happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_handle_check_suite_completed() -> None:
    """Finds step by head_sha, evaluates, and advances cascade."""
    dispatcher, workflow, step_svc, pr_svc, ws_svc, branch_svc, db = _build_dispatcher()

    step = _make_step(state="ci_pending", head_sha="sha_from_ci")
    workspace = _make_workspace()
    branch = _make_branch(workspace_id=workspace.id)

    step_svc.get_by_head_sha.return_value = step
    branch_svc.get.return_value = branch
    ws_svc.get.return_value = workspace

    # evaluate_step transitions to "completing" (PR merged by us)
    evaluated_step = MagicMock()
    evaluated_step.state = "completing"
    evaluated_step.cascade_id = step.cascade_id
    workflow.evaluate_step.return_value = evaluated_step

    workflow.advance_cascade.return_value = None

    payload = {
        "action": "completed",
        "check_suite": {"head_sha": "sha_from_ci", "conclusion": "success"},
    }

    result = await dispatcher.dispatch("check_suite", payload)

    assert result["handled"] is True
    workflow.evaluate_step.assert_called_once_with(db, step, workspace)
    workflow.advance_cascade.assert_called_once_with(db, step.cascade_id, workspace)


# ---------------------------------------------------------------------------
# _handle_check_suite_completed: no matching step
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_handle_check_suite_no_matching_step() -> None:
    """Ignores gracefully when no cascade step matches the head_sha."""
    dispatcher, workflow, step_svc, pr_svc, ws_svc, branch_svc, db = _build_dispatcher()

    step_svc.get_by_head_sha.return_value = None

    payload = {
        "action": "completed",
        "check_suite": {"head_sha": "unknown_sha", "conclusion": "success"},
    }

    result = await dispatcher.dispatch("check_suite", payload)

    assert result["handled"] is False
    workflow.evaluate_step.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_check_suite_completed: step not in ci_pending state
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_handle_check_suite_step_not_ci_pending() -> None:
    """Idempotent ignore when step is not in ci_pending state."""
    dispatcher, workflow, step_svc, pr_svc, ws_svc, branch_svc, db = _build_dispatcher()

    step = _make_step(state="merged", head_sha="sha_already_done")
    step_svc.get_by_head_sha.return_value = step

    payload = {
        "action": "completed",
        "check_suite": {"head_sha": "sha_already_done", "conclusion": "success"},
    }

    result = await dispatcher.dispatch("check_suite", payload)

    assert result["handled"] is False
    workflow.evaluate_step.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_pull_request_merged: happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_handle_pr_merged() -> None:
    """Finds step by PR, completes step, advances cascade."""
    dispatcher, workflow, step_svc, pr_svc, ws_svc, branch_svc, db = _build_dispatcher()

    pr = _make_pr(external_id=42)
    step = _make_step(state="completing")
    step.pull_request_id = pr.id
    workspace = _make_workspace()
    branch = _make_branch(workspace_id=workspace.id)

    pr_svc.get_by_external_id.return_value = pr
    step_svc.get_by_pull_request.return_value = step
    branch_svc.get.return_value = branch
    ws_svc.get.return_value = workspace

    # entity.complete_step is called via workflow
    workflow.entity = MagicMock()
    workflow.entity.complete_step = AsyncMock(return_value=step)
    workflow.advance_cascade.return_value = None

    payload = {
        "action": "closed",
        "pull_request": {"number": 42, "merged": True},
    }

    result = await dispatcher.dispatch("pull_request", payload)

    assert result["handled"] is True
    workflow.entity.complete_step.assert_called_once_with(db, step.id)
    workflow.advance_cascade.assert_called_once_with(db, step.cascade_id, workspace)


# ---------------------------------------------------------------------------
# _handle_pull_request_merged: no matching PR
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_handle_pr_merged_no_matching_pr() -> None:
    """Ignores gracefully when no PR matches the external_id."""
    dispatcher, workflow, step_svc, pr_svc, ws_svc, branch_svc, db = _build_dispatcher()

    pr_svc.get_by_external_id.return_value = None

    payload = {
        "action": "closed",
        "pull_request": {"number": 999, "merged": True},
    }

    result = await dispatcher.dispatch("pull_request", payload)

    assert result["handled"] is False
    workflow.entity.complete_step.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_pull_request_merged: step not in completing state
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_handle_pr_merged_step_not_completing() -> None:
    """Idempotent ignore when step is not in completing state."""
    dispatcher, workflow, step_svc, pr_svc, ws_svc, branch_svc, db = _build_dispatcher()

    pr = _make_pr(external_id=42)
    step = _make_step(state="merged")  # Already done

    pr_svc.get_by_external_id.return_value = pr
    step_svc.get_by_pull_request.return_value = step

    payload = {
        "action": "closed",
        "pull_request": {"number": 42, "merged": True},
    }

    result = await dispatcher.dispatch("pull_request", payload)

    assert result["handled"] is False
    workflow.entity.complete_step.assert_not_called()
