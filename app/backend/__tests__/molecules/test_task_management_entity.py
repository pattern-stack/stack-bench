from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from features.sprints.service import SprintService
from features.task_comments.service import TaskCommentService
from features.task_projects.service import TaskProjectService
from features.task_relations.service import TaskRelationService
from features.task_tags.service import TaskTagService
from features.tasks.service import TaskService
from molecules.entities.task_management_entity import TaskManagementEntity
from molecules.exceptions import (
    RelationCycleError,
    SprintNotFoundError,
    TaskHasBlockersError,
    TaskNotFoundError,
    TaskProjectNotFoundError,
)

# --- Init tests ---


@pytest.mark.unit
def test_task_management_entity_init() -> None:
    """Verify entity composes correct services."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    assert hasattr(entity, "task_service")
    assert hasattr(entity, "project_service")
    assert hasattr(entity, "sprint_service")
    assert hasattr(entity, "comment_service")
    assert hasattr(entity, "tag_service")
    assert hasattr(entity, "relation_service")


@pytest.mark.unit
def test_task_management_entity_services_are_correct_types() -> None:
    """Verify services are correct types."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    assert isinstance(entity.task_service, TaskService)
    assert isinstance(entity.project_service, TaskProjectService)
    assert isinstance(entity.sprint_service, SprintService)
    assert isinstance(entity.comment_service, TaskCommentService)
    assert isinstance(entity.tag_service, TaskTagService)
    assert isinstance(entity.relation_service, TaskRelationService)


# --- Task lifecycle tests ---


@pytest.mark.unit
async def test_get_task_raises_for_missing() -> None:
    """Verify TaskNotFoundError raised for missing task."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    entity.task_service.get = AsyncMock(return_value=None)

    with pytest.raises(TaskNotFoundError):
        await entity.get_task(uuid4())


@pytest.mark.unit
async def test_get_task_raises_for_soft_deleted() -> None:
    """Verify TaskNotFoundError raised for soft-deleted task."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_task = MagicMock()
    mock_task.is_deleted = True
    entity.task_service.get = AsyncMock(return_value=mock_task)

    with pytest.raises(TaskNotFoundError):
        await entity.get_task(uuid4())


@pytest.mark.unit
async def test_get_task_returns_valid_task() -> None:
    """Verify get_task returns a valid task."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_task = MagicMock()
    mock_task.is_deleted = False
    entity.task_service.get = AsyncMock(return_value=mock_task)

    result = await entity.get_task(uuid4())
    assert result is mock_task


@pytest.mark.unit
async def test_create_task_calls_service() -> None:
    """Verify create_task delegates to task service."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_task = MagicMock()
    entity.task_service.create = AsyncMock(return_value=mock_task)

    result = await entity.create_task(title="Test task", project_id=uuid4())
    assert result is mock_task
    entity.task_service.create.assert_awaited_once()


@pytest.mark.unit
async def test_delete_task_checks_blockers() -> None:
    """Verify delete_task raises when open blockers exist."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    task_id = uuid4()
    blocker_task_id = uuid4()

    mock_task = MagicMock()
    mock_task.is_deleted = False
    entity.task_service.get = AsyncMock(return_value=mock_task)

    mock_blocker_rel = MagicMock()
    mock_blocker_rel.source_task_id = blocker_task_id
    entity.relation_service.get_blockers = AsyncMock(return_value=[mock_blocker_rel])

    # The blocker task is open (not done/cancelled)
    mock_blocker_task = MagicMock()
    mock_blocker_task.is_deleted = False
    mock_blocker_task.state = "in_progress"

    # get_task returns the target task, but we need task_service.get for blocker
    async def get_side_effect(db_arg, tid):
        if tid == task_id:
            return mock_task
        return mock_blocker_task

    entity.task_service.get = AsyncMock(side_effect=get_side_effect)

    with pytest.raises(TaskHasBlockersError) as exc_info:
        await entity.delete_task(task_id)

    assert blocker_task_id in exc_info.value.blocker_ids


@pytest.mark.unit
async def test_delete_task_succeeds_when_blockers_done() -> None:
    """Verify delete_task succeeds when all blockers are done."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    task_id = uuid4()

    mock_task = MagicMock()
    mock_task.is_deleted = False
    entity.task_service.get = AsyncMock(return_value=mock_task)

    mock_blocker_rel = MagicMock()
    mock_blocker_rel.source_task_id = uuid4()
    entity.relation_service.get_blockers = AsyncMock(return_value=[mock_blocker_rel])

    # The blocker task is done
    mock_blocker_task = MagicMock()
    mock_blocker_task.is_deleted = False
    mock_blocker_task.state = "done"

    async def get_side_effect(db_arg, tid):
        if tid == task_id:
            return mock_task
        return mock_blocker_task

    entity.task_service.get = AsyncMock(side_effect=get_side_effect)

    await entity.delete_task(task_id)
    mock_task.soft_delete.assert_called_once()


@pytest.mark.unit
async def test_transition_task() -> None:
    """Verify transition_task calls transition on the model."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_task = MagicMock()
    mock_task.is_deleted = False
    entity.task_service.get = AsyncMock(return_value=mock_task)

    result = await entity.transition_task(uuid4(), "ready")
    mock_task.transition_to.assert_called_once_with("ready")
    assert result is mock_task


# --- Project tests ---


@pytest.mark.unit
async def test_get_project_raises_for_missing() -> None:
    """Verify TaskProjectNotFoundError raised for missing project."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    entity.project_service.get = AsyncMock(return_value=None)

    with pytest.raises(TaskProjectNotFoundError):
        await entity.get_project(uuid4())


@pytest.mark.unit
async def test_get_project_raises_for_soft_deleted() -> None:
    """Verify TaskProjectNotFoundError raised for soft-deleted project."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_project = MagicMock()
    mock_project.is_deleted = True
    entity.project_service.get = AsyncMock(return_value=mock_project)

    with pytest.raises(TaskProjectNotFoundError):
        await entity.get_project(uuid4())


@pytest.mark.unit
async def test_create_project_calls_service() -> None:
    """Verify create_project delegates to project service."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_project = MagicMock()
    entity.project_service.create = AsyncMock(return_value=mock_project)

    result = await entity.create_project(name="Test Project")
    assert result is mock_project
    entity.project_service.create.assert_awaited_once()


# --- Sprint tests ---


@pytest.mark.unit
async def test_get_sprint_raises_for_missing() -> None:
    """Verify SprintNotFoundError raised for missing sprint."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    entity.sprint_service.get = AsyncMock(return_value=None)

    with pytest.raises(SprintNotFoundError):
        await entity.get_sprint(uuid4())


@pytest.mark.unit
async def test_get_sprint_raises_for_soft_deleted() -> None:
    """Verify SprintNotFoundError raised for soft-deleted sprint."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_sprint = MagicMock()
    mock_sprint.is_deleted = True
    entity.sprint_service.get = AsyncMock(return_value=mock_sprint)

    with pytest.raises(SprintNotFoundError):
        await entity.get_sprint(uuid4())


@pytest.mark.unit
async def test_create_sprint_calls_service() -> None:
    """Verify create_sprint delegates to sprint service."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_sprint = MagicMock()
    entity.sprint_service.create = AsyncMock(return_value=mock_sprint)

    result = await entity.create_sprint(name="Sprint 1", project_id=uuid4())
    assert result is mock_sprint
    entity.sprint_service.create.assert_awaited_once()


@pytest.mark.unit
async def test_get_active_sprint_delegates() -> None:
    """Verify get_active_sprint delegates to sprint service."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_sprint = MagicMock()
    entity.sprint_service.get_active_sprint = AsyncMock(return_value=mock_sprint)

    project_id = uuid4()
    result = await entity.get_active_sprint(project_id)
    assert result is mock_sprint
    entity.sprint_service.get_active_sprint.assert_awaited_once_with(db, project_id)


# --- Comment tests ---


@pytest.mark.unit
async def test_add_comment_validates_task_exists() -> None:
    """Verify add_comment raises if task doesn't exist."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    entity.task_service.get = AsyncMock(return_value=None)

    with pytest.raises(TaskNotFoundError):
        await entity.add_comment(uuid4(), "Hello")


@pytest.mark.unit
async def test_add_comment_creates_comment() -> None:
    """Verify add_comment delegates to comment service."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_task = MagicMock()
    mock_task.is_deleted = False
    entity.task_service.get = AsyncMock(return_value=mock_task)

    mock_comment = MagicMock()
    entity.comment_service.create = AsyncMock(return_value=mock_comment)

    result = await entity.add_comment(uuid4(), "Hello")
    assert result is mock_comment
    entity.comment_service.create.assert_awaited_once()


# --- Tag tests ---


@pytest.mark.unit
async def test_apply_tag_validates_task_exists() -> None:
    """Verify apply_tag raises if task doesn't exist."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    entity.task_service.get = AsyncMock(return_value=None)

    with pytest.raises(TaskNotFoundError):
        await entity.apply_tag(uuid4(), uuid4())


@pytest.mark.unit
async def test_apply_tag_enforces_exclusivity() -> None:
    """Verify exclusive tags remove other tags from same group."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    task_id = uuid4()
    new_tag_id = uuid4()
    existing_tag_id = uuid4()

    mock_task = MagicMock()
    mock_task.is_deleted = False
    entity.task_service.get = AsyncMock(return_value=mock_task)

    # New tag is exclusive in group "priority"
    mock_new_tag = MagicMock()
    mock_new_tag.is_exclusive = True
    mock_new_tag.group = "priority"
    entity.tag_service.get = AsyncMock(return_value=mock_new_tag)

    # Existing tag is also in group "priority"
    mock_existing_tag = MagicMock()
    mock_existing_tag.id = existing_tag_id
    mock_existing_tag.group = "priority"
    entity.tag_service.get_task_tags = AsyncMock(return_value=[mock_existing_tag])

    entity.tag_service.remove_tag = AsyncMock()
    entity.tag_service.apply_tag = AsyncMock()

    await entity.apply_tag(task_id, new_tag_id)

    # Should have removed the existing tag first
    entity.tag_service.remove_tag.assert_awaited_once_with(db, task_id, existing_tag_id)
    entity.tag_service.apply_tag.assert_awaited_once_with(db, task_id, new_tag_id)


@pytest.mark.unit
async def test_apply_tag_skips_exclusivity_for_non_exclusive() -> None:
    """Verify non-exclusive tags don't remove other tags."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    task_id = uuid4()

    mock_task = MagicMock()
    mock_task.is_deleted = False
    entity.task_service.get = AsyncMock(return_value=mock_task)

    mock_tag = MagicMock()
    mock_tag.is_exclusive = False
    mock_tag.group = "priority"
    entity.tag_service.get = AsyncMock(return_value=mock_tag)

    entity.tag_service.get_task_tags = AsyncMock()
    entity.tag_service.apply_tag = AsyncMock()

    await entity.apply_tag(task_id, uuid4())

    # Should NOT have called get_task_tags (no exclusivity check needed)
    entity.tag_service.get_task_tags.assert_not_awaited()


# --- Relation tests ---


@pytest.mark.unit
async def test_add_relation_creates_relation() -> None:
    """Verify add_relation delegates to relation service."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_relation = MagicMock()
    entity.relation_service.create = AsyncMock(return_value=mock_relation)
    entity.relation_service.get_task_relations = AsyncMock(return_value=[])

    result = await entity.add_relation(uuid4(), uuid4(), "relates_to")
    assert result is mock_relation


@pytest.mark.unit
async def test_add_relation_detects_cycle_for_blocks() -> None:
    """Verify cycle detection for blocks relation type."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    source_id = uuid4()
    target_id = uuid4()

    # target already blocks source (target -> source exists)
    mock_existing_rel = MagicMock()
    mock_existing_rel.relation_type = "blocks"
    mock_existing_rel.source_task_id = target_id
    mock_existing_rel.target_task_id = source_id

    # When we look up relations for source_id, we find that target blocks source
    entity.relation_service.get_task_relations = AsyncMock(return_value=[mock_existing_rel])

    with pytest.raises(RelationCycleError):
        await entity.add_relation(source_id, target_id, "blocks")


@pytest.mark.unit
async def test_add_relation_detects_cycle_for_parent_of() -> None:
    """Verify cycle detection for parent_of relation type."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    source_id = uuid4()
    target_id = uuid4()

    # target is already parent of source (target -> source as parent_of)
    mock_existing_rel = MagicMock()
    mock_existing_rel.relation_type = "parent_of"
    mock_existing_rel.source_task_id = target_id
    mock_existing_rel.target_task_id = source_id

    entity.relation_service.get_task_relations = AsyncMock(return_value=[mock_existing_rel])

    with pytest.raises(RelationCycleError):
        await entity.add_relation(source_id, target_id, "parent_of")


@pytest.mark.unit
async def test_add_relation_no_cycle_check_for_relates_to() -> None:
    """Verify no cycle detection for relates_to type."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_relation = MagicMock()
    entity.relation_service.create = AsyncMock(return_value=mock_relation)

    # Should not call get_task_relations for cycle detection
    entity.relation_service.get_task_relations = AsyncMock()

    result = await entity.add_relation(uuid4(), uuid4(), "relates_to")
    assert result is mock_relation
    entity.relation_service.get_task_relations.assert_not_awaited()


@pytest.mark.unit
async def test_get_blockers_delegates() -> None:
    """Verify get_blockers delegates to relation service."""
    db = AsyncMock()
    entity = TaskManagementEntity(db)
    mock_relations = [MagicMock(), MagicMock()]
    entity.relation_service.get_blockers = AsyncMock(return_value=mock_relations)

    task_id = uuid4()
    result = await entity.get_blockers(task_id)
    assert result == mock_relations
    entity.relation_service.get_blockers.assert_awaited_once_with(db, task_id)
