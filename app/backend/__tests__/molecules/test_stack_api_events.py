"""Tests for event publishing in StackAPI methods."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from molecules.apis.stack_api import StackAPI
from molecules.events import (
    PULL_REQUEST_MARKED_READY,
    PULL_REQUEST_MERGED,
    REVIEW_COMMENT_CREATED,
    REVIEW_COMMENT_UPDATED,
    DomainEvent,
)


def _make_branch(*, state: str = "open", name: str = "feat/1", workspace_id=None):
    b = MagicMock()
    b.id = uuid4()
    b.name = name
    b.state = state
    b.workspace_id = workspace_id or uuid4()
    b.transition_to = MagicMock()
    return b


def _make_pr(*, state: str = "open", external_id: int = 42):
    pr = MagicMock()
    pr.id = uuid4()
    pr.state = state
    pr.external_id = external_id
    pr.transition_to = MagicMock(side_effect=lambda s: setattr(pr, "state", s))
    return pr


def _make_comment(*, comment_id=None):
    c = MagicMock()
    c.id = comment_id or uuid4()
    return c


@pytest.mark.asyncio
@pytest.mark.unit
@patch("molecules.apis.stack_api.publish", new_callable=AsyncMock)
async def test_merge_stack_publishes_merged_event(mock_publish: AsyncMock) -> None:
    """merge_stack publishes PULL_REQUEST_MERGED for each merged PR."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github=github)

    branch = _make_branch()
    pr = _make_pr(state="open")
    stack_id = uuid4()

    api.entity.get_stack_with_branches = AsyncMock(
        return_value={"stack": MagicMock(), "branches": [{"branch": branch, "pull_request": pr}]}
    )
    api.entity.get_branch_repo_context = AsyncMock(return_value=("owner", "repo", "main", "sha"))

    await api.merge_stack(stack_id)

    # Should have exactly one publish call (PULL_REQUEST_MERGED)
    assert mock_publish.call_count == 1
    event: DomainEvent = mock_publish.call_args_list[0][0][0]
    assert event.topic == PULL_REQUEST_MERGED
    assert event.entity_type == "pull_request"
    assert event.entity_id == pr.id
    assert event.source == "user_action"
    assert event.payload["branch_id"] == str(branch.id)
    assert event.payload["stack_id"] == str(stack_id)
    assert event.payload["external_id"] == pr.external_id


@pytest.mark.asyncio
@pytest.mark.unit
@patch("molecules.apis.stack_api.publish", new_callable=AsyncMock)
async def test_merge_stack_publishes_marked_ready_for_draft(mock_publish: AsyncMock) -> None:
    """merge_stack publishes PULL_REQUEST_MARKED_READY when draft is marked ready."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github=github)

    branch = _make_branch()
    pr = _make_pr(state="draft")
    stack_id = uuid4()

    api.entity.get_stack_with_branches = AsyncMock(
        return_value={"stack": MagicMock(), "branches": [{"branch": branch, "pull_request": pr}]}
    )
    api.entity.get_branch_repo_context = AsyncMock(return_value=("owner", "repo", "main", "sha"))

    await api.merge_stack(stack_id)

    # Should have two publish calls: MARKED_READY then MERGED
    assert mock_publish.call_count == 2
    ready_event: DomainEvent = mock_publish.call_args_list[0][0][0]
    assert ready_event.topic == PULL_REQUEST_MARKED_READY
    assert ready_event.entity_type == "pull_request"
    assert ready_event.entity_id == pr.id

    merge_event: DomainEvent = mock_publish.call_args_list[1][0][0]
    assert merge_event.topic == PULL_REQUEST_MERGED


@pytest.mark.asyncio
@pytest.mark.unit
@patch("molecules.apis.stack_api.publish", new_callable=AsyncMock)
async def test_merge_stack_publishes_for_each_pr(mock_publish: AsyncMock) -> None:
    """merge_stack publishes one MERGED event per merged PR."""
    db = AsyncMock()
    github = AsyncMock()
    api = StackAPI(db, github=github)

    branches_data = []
    for i in range(3):
        branches_data.append({"branch": _make_branch(name=f"feat/{i}"), "pull_request": _make_pr(external_id=i + 1)})

    api.entity.get_stack_with_branches = AsyncMock(
        return_value={"stack": MagicMock(), "branches": branches_data}
    )
    api.entity.get_branch_repo_context = AsyncMock(return_value=("owner", "repo", "main", "sha"))

    await api.merge_stack(uuid4())

    merged_events = [c[0][0] for c in mock_publish.call_args_list if c[0][0].topic == PULL_REQUEST_MERGED]
    assert len(merged_events) == 3


@pytest.mark.asyncio
@pytest.mark.unit
@patch("molecules.apis.stack_api.ReviewCommentResponse")
@patch("molecules.apis.stack_api.publish", new_callable=AsyncMock)
async def test_create_comment_publishes_event(mock_publish: AsyncMock, mock_resp: MagicMock) -> None:
    """create_comment publishes REVIEW_COMMENT_CREATED."""
    db = AsyncMock()
    api = StackAPI(db)

    comment = _make_comment()
    api._comment_svc.create = AsyncMock(return_value=comment)

    data = MagicMock()
    data.pull_request_id = uuid4()
    data.branch_id = uuid4()

    await api.create_comment(data)

    assert mock_publish.call_count == 1
    event: DomainEvent = mock_publish.call_args_list[0][0][0]
    assert event.topic == REVIEW_COMMENT_CREATED
    assert event.entity_type == "review_comment"
    assert event.entity_id == comment.id
    assert event.source == "user_action"
    assert event.payload["pull_request_id"] == str(data.pull_request_id)
    assert event.payload["branch_id"] == str(data.branch_id)


@pytest.mark.asyncio
@pytest.mark.unit
@patch("molecules.apis.stack_api.ReviewCommentResponse")
@patch("molecules.apis.stack_api.publish", new_callable=AsyncMock)
async def test_update_comment_publishes_event(mock_publish: AsyncMock, mock_resp: MagicMock) -> None:
    """update_comment publishes REVIEW_COMMENT_UPDATED."""
    db = AsyncMock()
    api = StackAPI(db)

    comment = _make_comment()
    api._comment_svc.update = AsyncMock(return_value=comment)

    data = MagicMock()
    data.resolved = True
    comment_id = uuid4()

    await api.update_comment(comment_id, data)

    assert mock_publish.call_count == 1
    event: DomainEvent = mock_publish.call_args_list[0][0][0]
    assert event.topic == REVIEW_COMMENT_UPDATED
    assert event.entity_type == "review_comment"
    assert event.entity_id == comment.id
    assert event.source == "user_action"
    assert event.payload["resolved"] is True
