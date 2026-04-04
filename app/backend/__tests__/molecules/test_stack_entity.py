from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from features.branches.service import BranchService
from features.pull_requests.service import PullRequestService
from features.stacks.service import StackService
from molecules.entities.stack_entity import StackEntity
from molecules.exceptions import (
    BranchNotFoundError,
    PullRequestNotFoundError,
    StackNotFoundError,
)


@pytest.mark.unit
def test_stack_entity_init() -> None:
    """Verify entity composes correct services."""
    db = AsyncMock()
    entity = StackEntity(db)
    assert hasattr(entity, "stack_service")
    assert hasattr(entity, "branch_service")
    assert hasattr(entity, "pr_service")


@pytest.mark.unit
def test_stack_entity_services_are_correct_types() -> None:
    """Verify services are correct types."""
    db = AsyncMock()
    entity = StackEntity(db)
    assert isinstance(entity.stack_service, StackService)
    assert isinstance(entity.branch_service, BranchService)
    assert isinstance(entity.pr_service, PullRequestService)


@pytest.mark.unit
async def test_get_stack_filters_soft_deleted() -> None:
    """Verify StackNotFoundError raised for soft-deleted stack."""
    db = AsyncMock()
    entity = StackEntity(db)
    mock_stack = MagicMock()
    mock_stack.is_deleted = True
    entity.stack_service.get = AsyncMock(return_value=mock_stack)

    with pytest.raises(StackNotFoundError):
        await entity.get_stack(uuid4())


@pytest.mark.unit
async def test_get_branch_filters_soft_deleted() -> None:
    """Verify BranchNotFoundError raised for soft-deleted branch."""
    db = AsyncMock()
    entity = StackEntity(db)
    mock_branch = MagicMock()
    mock_branch.is_deleted = True
    entity.branch_service.get = AsyncMock(return_value=mock_branch)

    with pytest.raises(BranchNotFoundError):
        await entity.get_branch(uuid4())


@pytest.mark.unit
async def test_get_pull_request_filters_soft_deleted() -> None:
    """Verify PullRequestNotFoundError raised for soft-deleted PR."""
    db = AsyncMock()
    entity = StackEntity(db)
    mock_pr = MagicMock()
    mock_pr.is_deleted = True
    entity.pr_service.get = AsyncMock(return_value=mock_pr)

    with pytest.raises(PullRequestNotFoundError):
        await entity.get_pull_request(uuid4())


# ---------------------------------------------------------------------------
# push_stack
# ---------------------------------------------------------------------------


def _make_mock_branch(
    name: str = "feature/1", state: str = "created", position: int = 1, stack_id: UUID | None = None
) -> MagicMock:
    branch = MagicMock()
    branch.id = uuid4()
    branch.name = name
    branch.state = state
    branch.position = position
    branch.stack_id = stack_id or uuid4()
    branch.workspace_id = uuid4()
    branch.head_sha = "abc123"
    branch.is_deleted = False
    return branch


def _make_mock_stack(state: str = "draft") -> MagicMock:
    stack = MagicMock()
    stack.id = uuid4()
    stack.name = "test-stack"
    stack.state = state
    stack.trunk = "main"
    stack.is_deleted = False
    return stack


def _make_mock_workspace() -> MagicMock:
    ws = MagicMock()
    ws.id = uuid4()
    ws.repo_url = "https://github.com/org/repo"
    return ws


@pytest.mark.unit
async def test_push_stack_transitions_created_to_pushed() -> None:
    """Push should transition branches from created to pushed."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_stack = _make_mock_stack(state="draft")
    mock_branch = _make_mock_branch(state="created")

    # Mock sync_stack to return our branch
    entity.sync_stack = AsyncMock(
        return_value={
            "branches": [{"branch": mock_branch, "pull_request": None}],
            "synced_count": 0,
            "created_count": 1,
        }
    )
    entity.get_stack = AsyncMock(return_value=mock_stack)

    await entity.push_stack(mock_stack.id, uuid4(), [])

    mock_branch.transition_to.assert_called_with("pushed")


@pytest.mark.unit
async def test_push_stack_activates_draft_stack() -> None:
    """Push on a draft stack should transition to active."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_stack = _make_mock_stack(state="draft")

    entity.sync_stack = AsyncMock(
        return_value={
            "branches": [],
            "synced_count": 0,
            "created_count": 0,
        }
    )
    entity.get_stack = AsyncMock(return_value=mock_stack)

    await entity.push_stack(mock_stack.id, uuid4(), [])

    mock_stack.transition_to.assert_called_with("active")


@pytest.mark.unit
async def test_push_stack_does_not_re_transition_pushed_branch() -> None:
    """Branch already in pushed state should not be transitioned again."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_stack = _make_mock_stack(state="active")
    mock_branch = _make_mock_branch(state="pushed")

    entity.sync_stack = AsyncMock(
        return_value={
            "branches": [{"branch": mock_branch, "pull_request": None}],
            "synced_count": 1,
            "created_count": 0,
        }
    )
    entity.get_stack = AsyncMock(return_value=mock_stack)

    await entity.push_stack(mock_stack.id, uuid4(), [])

    mock_branch.transition_to.assert_not_called()


# ---------------------------------------------------------------------------
# submit_stack
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_submit_stack_creates_draft_prs() -> None:
    """Submit should call github.create_pull_request with draft=True."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_stack = _make_mock_stack(state="active")
    mock_branch = _make_mock_branch(state="pushed", position=1)
    mock_workspace = _make_mock_workspace()

    entity.get_stack = AsyncMock(return_value=mock_stack)
    entity.get_stack_with_branches = AsyncMock(
        return_value={
            "stack": mock_stack,
            "branches": [{"branch": mock_branch, "pull_request": None}],
        }
    )
    entity.workspace_service.get = AsyncMock(return_value=mock_workspace)
    entity.pr_service.create = AsyncMock(
        return_value=MagicMock(id=uuid4(), external_id=42, external_url="https://github.com/org/repo/pull/42")
    )

    mock_github = AsyncMock()
    mock_github.create_pull_request = AsyncMock(
        return_value={
            "number": 42,
            "html_url": "https://github.com/org/repo/pull/42",
        }
    )

    result = await entity.submit_stack(mock_stack.id, mock_github)

    mock_github.create_pull_request.assert_called_once_with(
        "org",
        "repo",
        title=mock_branch.name,
        head=mock_branch.name,
        base="main",
        body=None,
        draft=True,
    )
    assert result["results"][0]["action"] == "created"
    assert result["results"][0]["pr_number"] == 42


@pytest.mark.unit
async def test_submit_stack_skips_branches_with_prs() -> None:
    """Branch with existing external_id should be skipped."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_stack = _make_mock_stack(state="active")
    mock_branch = _make_mock_branch(state="reviewing")
    mock_pr = MagicMock()
    mock_pr.external_id = 42

    entity.get_stack = AsyncMock(return_value=mock_stack)
    entity.get_stack_with_branches = AsyncMock(
        return_value={
            "stack": mock_stack,
            "branches": [{"branch": mock_branch, "pull_request": mock_pr}],
        }
    )

    mock_github = AsyncMock()
    result = await entity.submit_stack(mock_stack.id, mock_github)

    mock_github.create_pull_request.assert_not_called()
    assert result["results"][0]["action"] == "skipped"


@pytest.mark.unit
async def test_submit_stack_skips_unpushed_branches() -> None:
    """Branches in created state should be skipped."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_stack = _make_mock_stack(state="active")
    mock_branch = _make_mock_branch(state="created")

    entity.get_stack = AsyncMock(return_value=mock_stack)
    entity.get_stack_with_branches = AsyncMock(
        return_value={
            "stack": mock_stack,
            "branches": [{"branch": mock_branch, "pull_request": None}],
        }
    )

    mock_github = AsyncMock()
    result = await entity.submit_stack(mock_stack.id, mock_github)

    mock_github.create_pull_request.assert_not_called()
    assert result["results"][0]["reason"] == "not_pushed"


@pytest.mark.unit
async def test_submit_stack_transitions_branch_to_reviewing() -> None:
    """After submit, branch should transition to reviewing."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_stack = _make_mock_stack(state="active")
    mock_branch = _make_mock_branch(state="pushed", position=1)
    mock_workspace = _make_mock_workspace()

    entity.get_stack = AsyncMock(return_value=mock_stack)
    entity.get_stack_with_branches = AsyncMock(
        return_value={
            "stack": mock_stack,
            "branches": [{"branch": mock_branch, "pull_request": None}],
        }
    )
    entity.workspace_service.get = AsyncMock(return_value=mock_workspace)
    entity.pr_service.create = AsyncMock(return_value=MagicMock(id=uuid4()))

    mock_github = AsyncMock()
    mock_github.create_pull_request = AsyncMock(
        return_value={
            "number": 42,
            "html_url": "url",
        }
    )

    await entity.submit_stack(mock_stack.id, mock_github)

    mock_branch.transition_to.assert_called_with("reviewing")


# ---------------------------------------------------------------------------
# ready_stack
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_ready_stack_marks_draft_prs_open() -> None:
    """Ready should call github.mark_pr_ready and transition PR to open."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_branch = _make_mock_branch(state="reviewing")
    mock_pr = MagicMock()
    mock_pr.external_id = 42
    mock_pr.state = "draft"

    mock_workspace = _make_mock_workspace()

    entity.get_stack_with_branches = AsyncMock(
        return_value={
            "stack": _make_mock_stack(),
            "branches": [{"branch": mock_branch, "pull_request": mock_pr}],
        }
    )
    entity.workspace_service.get = AsyncMock(return_value=mock_workspace)

    mock_github = AsyncMock()
    result = await entity.ready_stack(uuid4(), mock_github)

    mock_github.mark_pr_ready.assert_called_once_with("org", "repo", 42)
    mock_pr.transition_to.assert_called_with("open")
    assert result["results"][0]["action"] == "marked_ready"


@pytest.mark.unit
async def test_ready_stack_skips_non_draft_prs() -> None:
    """PR already open should be skipped."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_branch = _make_mock_branch(state="ready")
    mock_pr = MagicMock()
    mock_pr.external_id = 42
    mock_pr.state = "open"

    entity.get_stack_with_branches = AsyncMock(
        return_value={
            "stack": _make_mock_stack(),
            "branches": [{"branch": mock_branch, "pull_request": mock_pr}],
        }
    )

    mock_github = AsyncMock()
    result = await entity.ready_stack(uuid4(), mock_github)

    mock_github.mark_pr_ready.assert_not_called()
    assert result["results"][0]["action"] == "skipped"


@pytest.mark.unit
async def test_ready_stack_filters_by_branch_ids() -> None:
    """Only specified branches should be marked ready."""
    db = AsyncMock()
    entity = StackEntity(db)

    branch_1 = _make_mock_branch(name="feature/1", state="reviewing")
    branch_2 = _make_mock_branch(name="feature/2", state="reviewing")

    pr_1 = MagicMock()
    pr_1.external_id = 10
    pr_1.state = "draft"
    pr_2 = MagicMock()
    pr_2.external_id = 11
    pr_2.state = "draft"

    mock_workspace = _make_mock_workspace()

    entity.get_stack_with_branches = AsyncMock(
        return_value={
            "stack": _make_mock_stack(),
            "branches": [
                {"branch": branch_1, "pull_request": pr_1},
                {"branch": branch_2, "pull_request": pr_2},
            ],
        }
    )
    entity.workspace_service.get = AsyncMock(return_value=mock_workspace)

    mock_github = AsyncMock()
    # Only mark branch_1 ready
    result = await entity.ready_stack(uuid4(), mock_github, branch_ids=[branch_1.id])

    # Only one call to mark_pr_ready
    mock_github.mark_pr_ready.assert_called_once_with("org", "repo", 10)
    assert len(result["results"]) == 1


@pytest.mark.unit
async def test_ready_stack_transitions_branch_to_ready() -> None:
    """Branch in reviewing state should transition to ready."""
    db = AsyncMock()
    entity = StackEntity(db)

    mock_branch = _make_mock_branch(state="reviewing")
    mock_pr = MagicMock()
    mock_pr.external_id = 42
    mock_pr.state = "draft"
    mock_workspace = _make_mock_workspace()

    entity.get_stack_with_branches = AsyncMock(
        return_value={
            "stack": _make_mock_stack(),
            "branches": [{"branch": mock_branch, "pull_request": mock_pr}],
        }
    )
    entity.workspace_service.get = AsyncMock(return_value=mock_workspace)

    mock_github = AsyncMock()
    await entity.ready_stack(uuid4(), mock_github)

    mock_branch.transition_to.assert_called_with("ready")
