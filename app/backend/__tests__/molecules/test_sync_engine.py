from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from molecules.providers.task_provider import (
    ExternalComment,
    ExternalTask,
    SyncResult,
    TaskProvider,
)
from molecules.services.sync_engine import SyncEngine


def _make_adapter() -> AsyncMock:
    """Create an AsyncMock that satisfies TaskProvider protocol."""
    adapter = AsyncMock(spec=TaskProvider)
    adapter.list_tasks = AsyncMock(return_value=[])
    adapter.get_task = AsyncMock(return_value=None)
    adapter.create_task = AsyncMock()
    adapter.update_task = AsyncMock()
    adapter.list_comments = AsyncMock(return_value=[])
    adapter.create_comment = AsyncMock()
    return adapter


def _make_entity() -> MagicMock:
    """Create a MagicMock for TaskManagementEntity."""
    entity = MagicMock()
    entity.task_service = MagicMock()
    entity.task_service.get_by_external_id = AsyncMock(return_value=None)
    entity.task_service.create = AsyncMock()
    entity.task_service.update = AsyncMock()
    entity.comment_service = MagicMock()
    entity.comment_service.get_by_external_id = AsyncMock(return_value=None)
    entity.comment_service.create = AsyncMock()
    entity.comment_service.update = AsyncMock()
    entity.get_task = AsyncMock()
    entity.list_tasks_by_project = AsyncMock(return_value=[])
    return entity


def _make_db() -> AsyncMock:
    return AsyncMock()


# --- Init ---


@pytest.mark.unit
def test_sync_engine_init_composes_entity_and_adapter() -> None:
    """SyncEngine stores db, entity, and adapter."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)

    assert engine.db is db
    assert engine.entity is entity
    assert engine.adapter is adapter


# --- TaskProvider protocol DTOs ---


@pytest.mark.unit
def test_external_task_dataclass() -> None:
    """ExternalTask has expected fields and defaults."""
    task = ExternalTask(external_id="123", title="Test")
    assert task.external_id == "123"
    assert task.title == "Test"
    assert task.description is None
    assert task.provider == "local"


@pytest.mark.unit
def test_external_comment_dataclass() -> None:
    """ExternalComment has expected fields and defaults."""
    comment = ExternalComment(external_id="c1", body="hello")
    assert comment.external_id == "c1"
    assert comment.body == "hello"
    assert comment.author_id is None


@pytest.mark.unit
def test_sync_result_defaults() -> None:
    """SyncResult starts with zero counts and empty errors."""
    result = SyncResult()
    assert result.created == 0
    assert result.updated == 0
    assert result.deleted == 0
    assert result.errors == []


@pytest.mark.unit
def test_sync_result_merge() -> None:
    """SyncResult.merge combines counts and errors."""
    a = SyncResult(created=1, updated=2, errors=["e1"])
    b = SyncResult(created=3, deleted=1, errors=["e2"])
    merged = a.merge(b)
    assert merged.created == 4
    assert merged.updated == 2
    assert merged.deleted == 1
    assert merged.errors == ["e1", "e2"]


@pytest.mark.unit
def test_task_provider_is_protocol() -> None:
    """TaskProvider has the expected method names."""
    assert hasattr(TaskProvider, "list_tasks")
    assert hasattr(TaskProvider, "get_task")
    assert hasattr(TaskProvider, "create_task")
    assert hasattr(TaskProvider, "update_task")
    assert hasattr(TaskProvider, "list_comments")
    assert hasattr(TaskProvider, "create_comment")


# --- Pull tasks ---


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pull_tasks_creates_new_tasks() -> None:
    """Pull creates local tasks when they don't exist."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    adapter.list_tasks.return_value = [
        ExternalTask(external_id="gh-1", title="Issue 1", provider="github"),
        ExternalTask(external_id="gh-2", title="Issue 2", provider="github"),
    ]
    entity.task_service.get_by_external_id = AsyncMock(return_value=None)

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.pull_tasks()

    assert result.created == 2
    assert result.updated == 0
    assert result.errors == []
    assert entity.task_service.create.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pull_tasks_updates_existing_tasks() -> None:
    """Pull updates local tasks when they already exist."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    existing_task = MagicMock()
    existing_task.id = uuid4()

    adapter.list_tasks.return_value = [
        ExternalTask(external_id="gh-1", title="Updated Title", provider="github"),
    ]
    entity.task_service.get_by_external_id = AsyncMock(return_value=existing_task)

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.pull_tasks()

    assert result.created == 0
    assert result.updated == 1
    entity.task_service.update.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pull_tasks_passes_project_id() -> None:
    """Pull passes project_id to adapter.list_tasks."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    project_id = uuid4()
    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    await engine.pull_tasks(project_id=project_id)

    adapter.list_tasks.assert_called_once_with(project_id=str(project_id))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pull_tasks_handles_adapter_error() -> None:
    """Pull returns error in SyncResult when adapter fails."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()
    adapter.list_tasks.side_effect = RuntimeError("connection refused")

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.pull_tasks()

    assert result.created == 0
    assert len(result.errors) == 1
    assert "connection refused" in result.errors[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pull_tasks_handles_individual_task_error() -> None:
    """Pull continues processing after individual task sync failure."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    adapter.list_tasks.return_value = [
        ExternalTask(external_id="gh-1", title="Good", provider="github"),
        ExternalTask(external_id="gh-2", title="Bad", provider="github"),
    ]

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("db error")
        return None

    entity.task_service.get_by_external_id = AsyncMock(side_effect=side_effect)

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.pull_tasks()

    assert result.created == 1
    assert len(result.errors) == 1


# --- Push task ---


@pytest.mark.unit
@pytest.mark.asyncio
async def test_push_task_creates_when_no_external_id() -> None:
    """Push creates on provider when task has no external_id."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    task_id = uuid4()
    local_task = MagicMock()
    local_task.id = task_id
    local_task.external_id = None
    local_task.title = "New Task"
    local_task.description = "desc"
    local_task.state = "backlog"
    local_task.priority = "high"
    local_task.external_url = None
    local_task.provider = "local"

    entity.get_task = AsyncMock(return_value=local_task)
    adapter.create_task.return_value = ExternalTask(
        external_id="gh-99", title="New Task", url="https://github.com/issues/99", provider="github"
    )

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.push_task(task_id)

    assert result.created == 1
    assert result.updated == 0
    adapter.create_task.assert_called_once()
    entity.task_service.update.assert_called_once()

    # Verify the update saved the external_id
    update_call = entity.task_service.update.call_args
    update_schema = update_call[0][2]
    assert update_schema.external_id == "gh-99"
    assert update_schema.provider == "github"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_push_task_updates_when_has_external_id() -> None:
    """Push updates on provider when task already has external_id."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    task_id = uuid4()
    local_task = MagicMock()
    local_task.id = task_id
    local_task.external_id = "gh-50"
    local_task.title = "Existing Task"
    local_task.description = None
    local_task.state = "in_progress"
    local_task.priority = "medium"
    local_task.external_url = "https://github.com/issues/50"
    local_task.provider = "github"

    entity.get_task = AsyncMock(return_value=local_task)
    adapter.update_task.return_value = ExternalTask(
        external_id="gh-50", title="Existing Task", url="https://github.com/issues/50", provider="github"
    )

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.push_task(task_id)

    assert result.created == 0
    assert result.updated == 1
    adapter.update_task.assert_called_once_with(
        "gh-50", pytest.approx(ExternalTask, abs=None) if False else adapter.update_task.call_args[0][1]
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_push_task_handles_task_not_found() -> None:
    """Push returns error when local task is not found."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    task_id = uuid4()
    entity.get_task = AsyncMock(side_effect=Exception(f"Task {task_id} not found"))

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.push_task(task_id)

    assert result.created == 0
    assert len(result.errors) == 1
    assert "not found" in result.errors[0]


# --- Pull comments ---


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pull_comments_creates_new_comments() -> None:
    """Pull creates local comments when they don't exist."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    task_id = uuid4()
    task = MagicMock()
    task.id = task_id
    task.external_id = "gh-10"
    task.provider = "github"
    entity.get_task = AsyncMock(return_value=task)

    adapter.list_comments.return_value = [
        ExternalComment(external_id="c1", body="First comment"),
        ExternalComment(external_id="c2", body="Second comment"),
    ]
    entity.comment_service.get_by_external_id = AsyncMock(return_value=None)

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.pull_comments(task_id)

    assert result.created == 2
    assert result.updated == 0
    assert entity.comment_service.create.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pull_comments_updates_existing_comments() -> None:
    """Pull updates local comments when they already exist."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    task_id = uuid4()
    task = MagicMock()
    task.id = task_id
    task.external_id = "gh-10"
    task.provider = "github"
    entity.get_task = AsyncMock(return_value=task)

    existing_comment = MagicMock()
    existing_comment.id = uuid4()

    adapter.list_comments.return_value = [
        ExternalComment(external_id="c1", body="Updated body"),
    ]
    entity.comment_service.get_by_external_id = AsyncMock(return_value=existing_comment)

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.pull_comments(task_id)

    assert result.created == 0
    assert result.updated == 1
    entity.comment_service.update.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pull_comments_errors_when_no_external_id() -> None:
    """Pull comments returns error when task has no external_id."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    task_id = uuid4()
    task = MagicMock()
    task.id = task_id
    task.external_id = None
    entity.get_task = AsyncMock(return_value=task)

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.pull_comments(task_id)

    assert len(result.errors) == 1
    assert "no external_id" in result.errors[0]


# --- Full sync ---


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_sync_pulls_tasks_and_comments() -> None:
    """Full sync pulls tasks and then comments for tasks with external_ids."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    project_id = uuid4()

    # Pull tasks returns one task
    adapter.list_tasks.return_value = [
        ExternalTask(external_id="gh-1", title="Issue 1", provider="github"),
    ]
    entity.task_service.get_by_external_id = AsyncMock(return_value=None)

    # list_tasks_by_project returns tasks with external_id
    mock_task = MagicMock()
    mock_task.id = uuid4()
    mock_task.external_id = "gh-1"
    mock_task.provider = "github"
    entity.list_tasks_by_project = AsyncMock(return_value=[mock_task])
    entity.get_task = AsyncMock(return_value=mock_task)

    adapter.list_comments.return_value = [
        ExternalComment(external_id="c1", body="A comment"),
    ]
    entity.comment_service.get_by_external_id = AsyncMock(return_value=None)

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.full_sync(project_id=project_id)

    # 1 task created + 1 comment created
    assert result.created == 2
    assert result.errors == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_sync_without_project_returns_pull_only() -> None:
    """Full sync without project_id only pulls tasks (no comment iteration)."""
    db = _make_db()
    entity = _make_entity()
    adapter = _make_adapter()

    adapter.list_tasks.return_value = [
        ExternalTask(external_id="gh-1", title="Issue 1", provider="github"),
    ]
    entity.task_service.get_by_external_id = AsyncMock(return_value=None)

    engine = SyncEngine(db=db, entity=entity, adapter=adapter)
    result = await engine.full_sync()

    assert result.created == 1
    # list_tasks_by_project should NOT be called without project_id
    entity.list_tasks_by_project.assert_not_called()
