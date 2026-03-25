"""Tests for push -> sync flow.

Tests the StackAPI.sync_stack method's branch result serialization,
verifying the response shape matches what the SyncStackResponse model expects.
Simulates what happens when st push calls POST /stacks/{id}/sync.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from molecules.apis.stack_api import StackAPI

# --- Helpers ---


def _make_branch_model(
    *,
    branch_id: object = None,
    stack_id: object = None,
    workspace_id: object = None,
    name: str = "branch-1",
    position: int = 1,
    head_sha: str = "abc123",
    state: str = "active",
) -> MagicMock:
    """Create a mock Branch ORM object that validates with BranchResponse."""
    branch = MagicMock()
    branch.id = branch_id or uuid4()
    branch.reference_number = None
    branch.stack_id = stack_id or uuid4()
    branch.workspace_id = workspace_id or uuid4()
    branch.name = name
    branch.position = position
    branch.head_sha = head_sha
    branch.state = state
    branch.is_deleted = False
    branch.created_at = datetime.now(UTC)
    branch.updated_at = datetime.now(UTC)
    return branch


def _make_pr_model(
    *,
    pr_id: object = None,
    branch_id: object = None,
    external_id: int | None = None,
    external_url: str | None = None,
    title: str = "PR title",
    state: str = "draft",
) -> MagicMock:
    """Create a mock PullRequest ORM object that validates with PullRequestResponse."""
    pr = MagicMock()
    pr.id = pr_id or uuid4()
    pr.reference_number = None
    pr.branch_id = branch_id or uuid4()
    pr.external_id = external_id
    pr.external_url = external_url
    pr.title = title
    pr.description = None
    pr.review_notes = None
    pr.state = state
    pr.is_deleted = False
    pr.created_at = datetime.now(UTC)
    pr.updated_at = datetime.now(UTC)
    return pr


# --- StackAPI.sync_stack serialization tests ---


@pytest.mark.unit
async def test_sync_stack_api_serializes_branches_with_prs() -> None:
    """Full sync flow: API should serialize branch + PR results properly.

    Validates the response shape matches SyncStackResponse:
    stack_id, synced_count, created_count, branches[{branch, pull_request}]
    """
    db = AsyncMock()
    api = StackAPI(db)

    stack_id = uuid4()
    workspace_id = uuid4()
    branch = _make_branch_model(stack_id=stack_id, name="user/my-stack/1-feature-a", head_sha="a" * 40)
    pr = _make_pr_model(branch_id=branch.id, external_id=101, external_url="https://github.com/owner/repo/pull/101")

    api.entity.sync_stack = AsyncMock(
        return_value={
            "branches": [{"branch": branch, "pull_request": pr}],
            "synced_count": 0,
            "created_count": 1,
        }
    )

    branches_data = [
        {
            "name": "user/my-stack/1-feature-a",
            "position": 1,
            "head_sha": "a" * 40,
            "pr_number": 101,
            "pr_url": "https://github.com/owner/repo/pull/101",
        },
    ]
    result = await api.sync_stack(stack_id, workspace_id, branches_data)

    # Verify response shape (SyncStackResponse fields)
    assert result["stack_id"] == str(stack_id)
    assert result["created_count"] == 1
    assert result["synced_count"] == 0
    assert isinstance(result["branches"], list)
    assert len(result["branches"]) == 1

    # Verify branch result shape (SyncBranchResult fields)
    br_result = result["branches"][0]
    assert isinstance(br_result["branch"], dict)
    assert isinstance(br_result["pull_request"], dict)
    assert br_result["branch"]["head_sha"] == "a" * 40
    assert br_result["branch"]["name"] == "user/my-stack/1-feature-a"
    assert br_result["pull_request"]["external_id"] == 101


@pytest.mark.unit
async def test_sync_stack_api_serializes_branch_without_pr() -> None:
    """Sync with no PR should have null pull_request in result."""
    db = AsyncMock()
    api = StackAPI(db)

    stack_id = uuid4()
    workspace_id = uuid4()
    branch = _make_branch_model(stack_id=stack_id, name="user/stack/1-feat", head_sha="b" * 40)

    api.entity.sync_stack = AsyncMock(
        return_value={
            "branches": [{"branch": branch, "pull_request": None}],
            "synced_count": 0,
            "created_count": 1,
        }
    )

    result = await api.sync_stack(
        stack_id, workspace_id, [{"name": "user/stack/1-feat", "position": 1, "head_sha": "b" * 40}]
    )

    assert result["branches"][0]["pull_request"] is None
    assert result["branches"][0]["branch"]["head_sha"] == "b" * 40


@pytest.mark.unit
async def test_sync_stack_api_update_existing_sha() -> None:
    """Second push updates SHAs without creating new branches."""
    db = AsyncMock()
    api = StackAPI(db)

    stack_id = uuid4()
    workspace_id = uuid4()
    branch = _make_branch_model(stack_id=stack_id, name="user/stack/1-feat", head_sha="c" * 40)

    api.entity.sync_stack = AsyncMock(
        return_value={
            "branches": [{"branch": branch, "pull_request": None}],
            "synced_count": 1,
            "created_count": 0,
        }
    )

    result = await api.sync_stack(
        stack_id, workspace_id, [{"name": "user/stack/1-feat", "position": 1, "head_sha": "c" * 40}]
    )

    assert result["synced_count"] == 1
    assert result["created_count"] == 0
    assert result["stack_id"] == str(stack_id)


@pytest.mark.unit
async def test_sync_stack_api_idempotent() -> None:
    """Same data twice: second call updates, not creates."""
    db = AsyncMock()
    api = StackAPI(db)

    stack_id = uuid4()
    workspace_id = uuid4()
    branch = _make_branch_model(stack_id=stack_id, name="user/stack/1-feat", head_sha="d" * 40)

    # Both calls return synced_count=1, created_count=0 (idempotent)
    api.entity.sync_stack = AsyncMock(
        return_value={
            "branches": [{"branch": branch, "pull_request": None}],
            "synced_count": 1,
            "created_count": 0,
        }
    )

    data = [{"name": "user/stack/1-feat", "position": 1, "head_sha": "d" * 40}]
    result1 = await api.sync_stack(stack_id, workspace_id, data)
    result2 = await api.sync_stack(stack_id, workspace_id, data)

    assert result1["synced_count"] == result2["synced_count"]
    assert result1["created_count"] == result2["created_count"]


@pytest.mark.unit
async def test_sync_stack_api_multiple_branches() -> None:
    """Sync with two branches + PRs should serialize both."""
    db = AsyncMock()
    api = StackAPI(db)

    stack_id = uuid4()
    workspace_id = uuid4()

    branch_a = _make_branch_model(stack_id=stack_id, name="user/my-stack/1-feature-a", position=1, head_sha="a" * 40)
    pr_a = _make_pr_model(branch_id=branch_a.id, external_id=101, external_url="https://github.com/owner/repo/pull/101")

    branch_b = _make_branch_model(stack_id=stack_id, name="user/my-stack/2-feature-b", position=2, head_sha="b" * 40)
    pr_b = _make_pr_model(branch_id=branch_b.id, external_id=102, external_url="https://github.com/owner/repo/pull/102")

    api.entity.sync_stack = AsyncMock(
        return_value={
            "branches": [
                {"branch": branch_a, "pull_request": pr_a},
                {"branch": branch_b, "pull_request": pr_b},
            ],
            "synced_count": 0,
            "created_count": 2,
        }
    )

    result = await api.sync_stack(
        stack_id,
        workspace_id,
        [
            {"name": "user/my-stack/1-feature-a", "position": 1, "head_sha": "a" * 40, "pr_number": 101},
            {"name": "user/my-stack/2-feature-b", "position": 2, "head_sha": "b" * 40, "pr_number": 102},
        ],
    )

    assert result["created_count"] == 2
    assert len(result["branches"]) == 2
    assert result["branches"][0]["branch"]["head_sha"] == "a" * 40
    assert result["branches"][0]["pull_request"]["external_id"] == 101
    assert result["branches"][1]["branch"]["head_sha"] == "b" * 40
    assert result["branches"][1]["pull_request"]["external_id"] == 102
