from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

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
