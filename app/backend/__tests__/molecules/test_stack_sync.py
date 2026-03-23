"""Tests for stack sync functionality.

Tests the sync_stack method on StackEntity and StackAPI which
reconciles DB state with branch/PR data from the client.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from molecules.apis.stack_api import StackAPI
from molecules.entities.stack_entity import StackEntity


def _make_branch(
    *,
    branch_id=None,
    stack_id=None,
    name="branch-1",
    position=1,
    head_sha="abc123",
    is_deleted=False,
):
    """Create a mock Branch object."""
    branch = MagicMock()
    branch.id = branch_id or uuid4()
    branch.stack_id = stack_id or uuid4()
    branch.name = name
    branch.position = position
    branch.head_sha = head_sha
    branch.is_deleted = is_deleted
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


# --- StackEntity.sync_stack tests ---


@pytest.mark.unit
async def test_sync_stack_updates_existing_branch_sha() -> None:
    """Sync should update head_sha for existing branches."""
    db = AsyncMock()
    entity = StackEntity(db)

    stack_id = uuid4()
    workspace_id = uuid4()
    branch = _make_branch(stack_id=stack_id, name="feature-1", head_sha="old_sha")

    # Mock: stack exists
    mock_stack = MagicMock()
    mock_stack.is_deleted = False
    entity.stack_service.get = AsyncMock(return_value=mock_stack)

    # Mock: branch found by name
    entity.branch_service.get_by_name = AsyncMock(return_value=branch)

    # Mock: update returns updated branch
    updated_branch = _make_branch(branch_id=branch.id, stack_id=stack_id, name="feature-1", head_sha="new_sha")
    entity.branch_service.update = AsyncMock(return_value=updated_branch)

    # Mock: no PR
    entity.pr_service.get_by_branch = AsyncMock(return_value=None)

    result = await entity.sync_stack(
        stack_id,
        workspace_id,
        [{"name": "feature-1", "position": 1, "head_sha": "new_sha"}],
    )

    assert result["synced_count"] == 1
    assert result["created_count"] == 0
    entity.branch_service.update.assert_called_once()


@pytest.mark.unit
async def test_sync_stack_creates_new_branch() -> None:
    """Sync should create branch when it does not exist."""
    db = AsyncMock()
    entity = StackEntity(db)

    stack_id = uuid4()
    workspace_id = uuid4()

    # Mock: stack exists
    mock_stack = MagicMock()
    mock_stack.is_deleted = False
    entity.stack_service.get = AsyncMock(return_value=mock_stack)

    # Mock: branch not found
    entity.branch_service.get_by_name = AsyncMock(return_value=None)

    # Mock: create returns new branch
    new_branch = _make_branch(stack_id=stack_id, name="feature-1", head_sha="abc123")
    entity.branch_service.create = AsyncMock(return_value=new_branch)

    # Mock: no PR
    entity.pr_service.get_by_branch = AsyncMock(return_value=None)

    result = await entity.sync_stack(
        stack_id,
        workspace_id,
        [{"name": "feature-1", "position": 1, "head_sha": "abc123"}],
    )

    assert result["synced_count"] == 0
    assert result["created_count"] == 1
    entity.branch_service.create.assert_called_once()


@pytest.mark.unit
async def test_sync_stack_links_new_pr() -> None:
    """Sync should create and link PR when pr_number provided and no PR exists."""
    db = AsyncMock()
    entity = StackEntity(db)

    stack_id = uuid4()
    workspace_id = uuid4()
    branch = _make_branch(stack_id=stack_id, name="feature-1")

    # Mock: stack exists
    mock_stack = MagicMock()
    mock_stack.is_deleted = False
    entity.stack_service.get = AsyncMock(return_value=mock_stack)

    # Mock: branch found
    entity.branch_service.get_by_name = AsyncMock(return_value=branch)
    updated_branch = _make_branch(branch_id=branch.id, stack_id=stack_id, name="feature-1", head_sha="sha123")
    entity.branch_service.update = AsyncMock(return_value=updated_branch)

    # Mock: no existing PR
    entity.pr_service.get_by_branch = AsyncMock(return_value=None)

    # Mock: create PR
    new_pr = _make_pr(branch_id=branch.id, external_id=42, external_url="https://github.com/o/r/pull/42")
    entity.pr_service.create = AsyncMock(return_value=new_pr)

    # Mock: update PR (for linking external)
    entity.pr_service.update = AsyncMock(return_value=new_pr)

    result = await entity.sync_stack(
        stack_id,
        workspace_id,
        [
            {
                "name": "feature-1",
                "position": 1,
                "head_sha": "sha123",
                "pr_number": 42,
                "pr_url": "https://github.com/o/r/pull/42",
            }
        ],
    )

    entity.pr_service.create.assert_called_once()
    assert result["synced_count"] == 1


@pytest.mark.unit
async def test_sync_stack_updates_existing_pr_external_id() -> None:
    """Sync should update PR external_id if it changed."""
    db = AsyncMock()
    entity = StackEntity(db)

    stack_id = uuid4()
    workspace_id = uuid4()
    branch = _make_branch(stack_id=stack_id, name="feature-1")

    # Mock: stack exists
    mock_stack = MagicMock()
    mock_stack.is_deleted = False
    entity.stack_service.get = AsyncMock(return_value=mock_stack)

    # Mock: branch found
    entity.branch_service.get_by_name = AsyncMock(return_value=branch)
    entity.branch_service.update = AsyncMock(return_value=branch)

    # Mock: existing PR with different external_id
    existing_pr = _make_pr(branch_id=branch.id, external_id=41, state="draft")
    entity.pr_service.get_by_branch = AsyncMock(return_value=existing_pr)
    entity.pr_service.update = AsyncMock(return_value=existing_pr)

    await entity.sync_stack(
        stack_id,
        workspace_id,
        [
            {
                "name": "feature-1",
                "position": 1,
                "head_sha": "sha123",
                "pr_number": 42,
                "pr_url": "https://github.com/o/r/pull/42",
            }
        ],
    )

    # Should call update to re-link external PR
    entity.pr_service.update.assert_called()


@pytest.mark.unit
async def test_sync_stack_multiple_branches() -> None:
    """Sync should process multiple branches, creating and updating as needed."""
    db = AsyncMock()
    entity = StackEntity(db)

    stack_id = uuid4()
    workspace_id = uuid4()

    # Mock: stack exists
    mock_stack = MagicMock()
    mock_stack.is_deleted = False
    entity.stack_service.get = AsyncMock(return_value=mock_stack)

    existing_branch = _make_branch(stack_id=stack_id, name="feature-1")

    def get_by_name_side_effect(db, sid, name):
        if name == "feature-1":
            return existing_branch
        return None

    entity.branch_service.get_by_name = AsyncMock(side_effect=get_by_name_side_effect)
    entity.branch_service.update = AsyncMock(return_value=existing_branch)

    new_branch = _make_branch(stack_id=stack_id, name="feature-2", position=2)
    entity.branch_service.create = AsyncMock(return_value=new_branch)

    entity.pr_service.get_by_branch = AsyncMock(return_value=None)

    result = await entity.sync_stack(
        stack_id,
        workspace_id,
        [
            {"name": "feature-1", "position": 1, "head_sha": "sha1"},
            {"name": "feature-2", "position": 2, "head_sha": "sha2"},
        ],
    )

    assert result["synced_count"] == 1
    assert result["created_count"] == 1


@pytest.mark.unit
async def test_sync_stack_idempotent() -> None:
    """Calling sync twice with same data should produce same result."""
    db = AsyncMock()
    entity = StackEntity(db)

    stack_id = uuid4()
    workspace_id = uuid4()
    branch = _make_branch(stack_id=stack_id, name="feature-1", head_sha="sha1")

    mock_stack = MagicMock()
    mock_stack.is_deleted = False
    entity.stack_service.get = AsyncMock(return_value=mock_stack)
    entity.branch_service.get_by_name = AsyncMock(return_value=branch)
    entity.branch_service.update = AsyncMock(return_value=branch)
    entity.pr_service.get_by_branch = AsyncMock(return_value=None)

    branches_data = [{"name": "feature-1", "position": 1, "head_sha": "sha1"}]

    result1 = await entity.sync_stack(stack_id, workspace_id, branches_data)
    result2 = await entity.sync_stack(stack_id, workspace_id, branches_data)

    assert result1["synced_count"] == result2["synced_count"]


# --- StackAPI.sync_stack tests ---


def _make_stack_mock(stack_id=None, project_id=None):
    """Create a mock Stack with valid attributes for StackResponse validation."""
    from datetime import UTC, datetime

    stack = MagicMock()
    stack.id = stack_id or uuid4()
    stack.reference_number = "STK-001"
    stack.project_id = project_id or uuid4()
    stack.name = "test-stack"
    stack.base_branch_id = None
    stack.trunk = "main"
    stack.state = "active"
    stack.created_at = datetime.now(UTC)
    stack.updated_at = datetime.now(UTC)
    return stack


@pytest.mark.unit
async def test_stack_api_sync_stack_delegates_to_entity() -> None:
    """StackAPI.sync_stack should delegate to StackEntity.sync_stack."""
    db = AsyncMock()
    api = StackAPI(db)

    stack_id = uuid4()
    workspace_id = uuid4()

    # Mock entity's sync_stack
    mock_result = {
        "branches": [],
        "synced_count": 1,
        "created_count": 0,
    }
    api.entity.sync_stack = AsyncMock(return_value=mock_result)

    mock_stack = _make_stack_mock(stack_id=stack_id)
    api.entity.get_stack_with_branches = AsyncMock(return_value={"stack": mock_stack, "branches": []})

    branches = [{"name": "feature-1", "position": 1, "head_sha": "sha1"}]
    result = await api.sync_stack(stack_id, workspace_id, branches)

    api.entity.sync_stack.assert_called_once_with(stack_id, workspace_id, branches)
    assert "synced_count" in result
    assert "created_count" in result
    assert result["synced_count"] == 1
    assert result["created_count"] == 0


# --- Router tests ---


@pytest.mark.unit
def test_sync_stack_route_registered() -> None:
    """Verify POST /stacks/{stack_id}/sync route exists."""
    from organisms.api.app import app

    routes = [getattr(r, "path", str(r)) for r in app.routes]
    assert any("/sync" in r for r in routes)
