"""Tests for needs-restack detection.

Tests the get_behind_count method on GitHubAdapter and the
_compute_restack_flags / get_stack_detail enrichment in StackAPI.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from molecules.apis.stack_api import StackAPI
from molecules.providers.github_adapter import GitHubAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_branch(
    *,
    branch_id=None,
    stack_id=None,
    workspace_id=None,
    name="branch-1",
    position=1,
    head_sha="abc123",
    state="active",
    is_deleted=False,
):
    """Create a mock Branch object."""
    from datetime import UTC, datetime

    branch = MagicMock()
    branch.id = branch_id or uuid4()
    branch.stack_id = stack_id or uuid4()
    branch.workspace_id = workspace_id or uuid4()
    branch.name = name
    branch.position = position
    branch.head_sha = head_sha
    branch.state = state
    branch.is_deleted = is_deleted
    branch.reference_number = None
    branch.created_at = datetime.now(UTC)
    branch.updated_at = datetime.now(UTC)
    return branch


def _make_pr(
    *,
    pr_id=None,
    branch_id=None,
    external_id=None,
    external_url=None,
    state="draft",
    is_deleted=False,
):
    """Create a mock PullRequest object."""
    pr = MagicMock()
    pr.id = pr_id or uuid4()
    pr.branch_id = branch_id or uuid4()
    pr.external_id = external_id
    pr.external_url = external_url
    pr.state = state
    pr.is_deleted = is_deleted
    return pr


def _make_stack(*, stack_id=None, project_id=None, trunk="main"):
    """Create a mock Stack with valid attributes for StackResponse validation."""
    from datetime import UTC, datetime

    stack = MagicMock()
    stack.id = stack_id or uuid4()
    stack.reference_number = "STK-001"
    stack.project_id = project_id or uuid4()
    stack.name = "test-stack"
    stack.base_branch_id = None
    stack.trunk = trunk
    stack.state = "active"
    stack.created_at = datetime.now(UTC)
    stack.updated_at = datetime.now(UTC)
    return stack


def _make_workspace(*, workspace_id=None, repo_url="https://github.com/owner/repo"):
    """Create a mock Workspace."""
    ws = MagicMock()
    ws.id = workspace_id or uuid4()
    ws.repo_url = repo_url
    return ws


# ---------------------------------------------------------------------------
# Phase 1: GitHubAdapter.get_behind_count
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_get_behind_count_returns_integer() -> None:
    """get_behind_count should return the behind_by integer from compare API."""
    adapter = GitHubAdapter.__new__(GitHubAdapter)
    adapter._cache = AsyncMock()
    adapter._cache.get = AsyncMock(return_value=None)
    adapter._cache.set = AsyncMock()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"behind_by": 3}
    adapter._client = AsyncMock()
    adapter._client.get = AsyncMock(return_value=mock_response)

    result = await adapter.get_behind_count("owner", "repo", "main", "feature-1")

    assert result == 3
    adapter._client.get.assert_called_once_with("/repos/owner/repo/compare/main...feature-1")


@pytest.mark.unit
async def test_get_behind_count_caches_result() -> None:
    """get_behind_count should cache and reuse the result on second call."""
    adapter = GitHubAdapter.__new__(GitHubAdapter)
    adapter._cache = AsyncMock()
    # First call: cache miss; second call: cache hit
    adapter._cache.get = AsyncMock(side_effect=[None, 3])
    adapter._cache.set = AsyncMock()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"behind_by": 3}
    adapter._client = AsyncMock()
    adapter._client.get = AsyncMock(return_value=mock_response)

    result1 = await adapter.get_behind_count("owner", "repo", "main", "feature-1")
    result2 = await adapter.get_behind_count("owner", "repo", "main", "feature-1")

    assert result1 == 3
    assert result2 == 3
    # Only one HTTP request should have been made
    assert adapter._client.get.call_count == 1


@pytest.mark.unit
async def test_get_behind_count_zero() -> None:
    """get_behind_count should return 0 when behind_by is 0."""
    adapter = GitHubAdapter.__new__(GitHubAdapter)
    adapter._cache = AsyncMock()
    adapter._cache.get = AsyncMock(return_value=None)
    adapter._cache.set = AsyncMock()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"behind_by": 0}
    adapter._client = AsyncMock()
    adapter._client.get = AsyncMock(return_value=mock_response)

    result = await adapter.get_behind_count("owner", "repo", "main", "feature-1")

    assert result == 0


# ---------------------------------------------------------------------------
# Phase 2: StackAPI._compute_restack_flags and get_stack_detail
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_compute_restack_flags_parallel() -> None:
    """_compute_restack_flags should return [True, False, True] for behind counts [2, 0, 5]."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github=github)

    stack_id = uuid4()
    workspace_id = uuid4()
    stack = _make_stack(stack_id=stack_id)

    branches = [
        {"branch": _make_branch(position=1, workspace_id=workspace_id, name="b1"), "pull_request": None},
        {"branch": _make_branch(position=2, workspace_id=workspace_id, name="b2"), "pull_request": None},
        {"branch": _make_branch(position=3, workspace_id=workspace_id, name="b3"), "pull_request": None},
    ]

    workspace = _make_workspace(workspace_id=workspace_id)
    api.entity.workspace_service.get = AsyncMock(return_value=workspace)
    github.get_behind_count = AsyncMock(side_effect=[2, 0, 5])

    flags = await api._compute_restack_flags(stack, branches)

    assert flags == [True, False, True]


@pytest.mark.unit
async def test_merged_branch_skipped() -> None:
    """A branch with state='merged' should always return needs_restack=False."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github=github)

    workspace_id = uuid4()
    stack = _make_stack()

    branches = [
        {"branch": _make_branch(position=1, workspace_id=workspace_id, state="merged"), "pull_request": None},
    ]

    workspace = _make_workspace(workspace_id=workspace_id)
    api.entity.workspace_service.get = AsyncMock(return_value=workspace)
    # Should NOT be called for merged branches
    github.get_behind_count = AsyncMock(return_value=5)

    flags = await api._compute_restack_flags(stack, branches)

    assert flags == [False]
    github.get_behind_count.assert_not_called()


@pytest.mark.unit
async def test_merged_pr_skipped() -> None:
    """A branch with a merged PR should always return needs_restack=False."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github=github)

    workspace_id = uuid4()
    stack = _make_stack()

    merged_pr = _make_pr(state="merged")
    branches = [
        {"branch": _make_branch(position=1, workspace_id=workspace_id, state="active"), "pull_request": merged_pr},
    ]

    workspace = _make_workspace(workspace_id=workspace_id)
    api.entity.workspace_service.get = AsyncMock(return_value=workspace)
    github.get_behind_count = AsyncMock(return_value=5)

    flags = await api._compute_restack_flags(stack, branches)

    assert flags == [False]
    github.get_behind_count.assert_not_called()


@pytest.mark.unit
async def test_github_error_returns_false() -> None:
    """When get_behind_count raises an exception, that branch gets False."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github=github)

    workspace_id = uuid4()
    stack = _make_stack()

    branches = [
        {"branch": _make_branch(position=1, workspace_id=workspace_id), "pull_request": None},
    ]

    workspace = _make_workspace(workspace_id=workspace_id)
    api.entity.workspace_service.get = AsyncMock(return_value=workspace)
    github.get_behind_count = AsyncMock(side_effect=Exception("API error"))

    flags = await api._compute_restack_flags(stack, branches)

    assert flags == [False]


@pytest.mark.unit
async def test_no_github_adapter_all_false() -> None:
    """When github adapter is None, all branches get needs_restack=False."""
    db = AsyncMock()
    api = StackAPI(db, github=None)

    stack_id = uuid4()
    workspace_id = uuid4()
    stack = _make_stack(stack_id=stack_id)

    branch1 = _make_branch(position=1, workspace_id=workspace_id, name="b1")
    branch2 = _make_branch(position=2, workspace_id=workspace_id, name="b2")

    api.entity.get_stack_with_branches = AsyncMock(
        return_value={
            "stack": stack,
            "branches": [
                {"branch": branch1, "pull_request": None},
                {"branch": branch2, "pull_request": None},
            ],
        }
    )

    result = await api.get_stack_detail(stack_id)

    for b in result["branches"]:
        assert b["needs_restack"] is False


@pytest.mark.unit
async def test_position_1_uses_trunk() -> None:
    """Branch at position 1 should compare against stack.trunk."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github=github)

    workspace_id = uuid4()
    stack = _make_stack(trunk="main")

    branches = [
        {
            "branch": _make_branch(position=1, workspace_id=workspace_id, head_sha="sha1", name="b1"),
            "pull_request": None,
        },
    ]

    workspace = _make_workspace(workspace_id=workspace_id)
    api.entity.workspace_service.get = AsyncMock(return_value=workspace)
    github.get_behind_count = AsyncMock(return_value=2)

    await api._compute_restack_flags(stack, branches)

    github.get_behind_count.assert_called_once_with("owner", "repo", "main", "sha1")


@pytest.mark.unit
async def test_position_n_uses_previous_branch() -> None:
    """Branch at position N should compare against branch at position N-1's name."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github=github)

    workspace_id = uuid4()
    stack = _make_stack(trunk="main")

    branches = [
        {
            "branch": _make_branch(position=1, workspace_id=workspace_id, head_sha="sha1", name="b1"),
            "pull_request": None,
        },
        {
            "branch": _make_branch(position=2, workspace_id=workspace_id, head_sha="sha2", name="b2"),
            "pull_request": None,
        },
        {
            "branch": _make_branch(position=3, workspace_id=workspace_id, head_sha="sha3", name="b3"),
            "pull_request": None,
        },
    ]

    workspace = _make_workspace(workspace_id=workspace_id)
    api.entity.workspace_service.get = AsyncMock(return_value=workspace)
    github.get_behind_count = AsyncMock(return_value=0)

    await api._compute_restack_flags(stack, branches)

    calls = github.get_behind_count.call_args_list
    # Position 1 → trunk
    assert calls[0].args == ("owner", "repo", "main", "sha1")
    # Position 2 → branch 1's name
    assert calls[1].args == ("owner", "repo", "b1", "sha2")
    # Position 3 → branch 2's name
    assert calls[2].args == ("owner", "repo", "b2", "sha3")
