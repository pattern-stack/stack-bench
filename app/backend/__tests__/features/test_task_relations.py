from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.task_relations.models import TaskRelation
from features.task_relations.schemas.input import TaskRelationCreate, TaskRelationUpdate
from features.task_relations.schemas.output import TaskRelationResponse
from features.task_relations.service import TaskRelationService

# --- Model tests ---


@pytest.mark.unit
def test_task_relation_model_fields() -> None:
    """Verify all domain fields, FK fields, and sync fields exist on the model class."""
    # Domain fields
    assert hasattr(TaskRelation, "source_task_id")
    assert hasattr(TaskRelation, "target_task_id")
    assert hasattr(TaskRelation, "relation_type")
    # External sync fields
    assert hasattr(TaskRelation, "external_id")
    assert hasattr(TaskRelation, "external_url")
    assert hasattr(TaskRelation, "provider")
    assert hasattr(TaskRelation, "last_synced_at")


@pytest.mark.unit
def test_task_relation_pattern_config() -> None:
    """Verify Pattern inner class: entity, reference_prefix."""
    assert TaskRelation.Pattern.entity == "task_relation"
    assert TaskRelation.Pattern.reference_prefix == "TRL"


@pytest.mark.unit
def test_task_relation_tablename() -> None:
    """Verify __tablename__ is task_relations."""
    assert TaskRelation.__tablename__ == "task_relations"


@pytest.mark.unit
def test_task_relation_unique_constraint() -> None:
    """Verify uniqueness constraint on (source_task_id, target_task_id, relation_type)."""
    constraints = TaskRelation.__table_args__
    assert len(constraints) >= 1
    uq = constraints[0]
    assert uq.name == "uq_task_relation"


@pytest.mark.unit
def test_task_relation_is_base_pattern() -> None:
    """Verify TaskRelation uses BasePattern (no state machine)."""
    from pattern_stack.atoms.patterns import BasePattern

    assert issubclass(TaskRelation, BasePattern)
    assert not hasattr(TaskRelation, "state") or not hasattr(TaskRelation.Pattern, "states")


# --- Schema tests ---


@pytest.mark.unit
def test_task_relation_create_minimal() -> None:
    """TaskRelationCreate with required fields only."""
    source_id = uuid4()
    target_id = uuid4()
    data = TaskRelationCreate(
        source_task_id=source_id,
        target_task_id=target_id,
        relation_type="blocks",
    )
    assert data.source_task_id == source_id
    assert data.target_task_id == target_id
    assert data.relation_type == "blocks"
    assert data.provider == "local"
    assert data.external_id is None
    assert data.external_url is None
    assert data.last_synced_at is None


@pytest.mark.unit
def test_task_relation_create_full() -> None:
    """TaskRelationCreate with all fields populated."""
    from datetime import UTC, datetime

    source_id = uuid4()
    target_id = uuid4()
    now = datetime.now(UTC)

    data = TaskRelationCreate(
        source_task_id=source_id,
        target_task_id=target_id,
        relation_type="parent_of",
        external_id="REL-1",
        external_url="https://github.com/org/repo/issues/1",
        provider="github",
        last_synced_at=now,
    )
    assert data.source_task_id == source_id
    assert data.target_task_id == target_id
    assert data.relation_type == "parent_of"
    assert data.external_id == "REL-1"
    assert data.external_url == "https://github.com/org/repo/issues/1"
    assert data.provider == "github"
    assert data.last_synced_at == now


@pytest.mark.unit
def test_task_relation_create_requires_source_task_id() -> None:
    """Omitting source_task_id raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskRelationCreate(target_task_id=uuid4(), relation_type="blocks")  # type: ignore[call-arg]


@pytest.mark.unit
def test_task_relation_create_requires_target_task_id() -> None:
    """Omitting target_task_id raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskRelationCreate(source_task_id=uuid4(), relation_type="blocks")  # type: ignore[call-arg]


@pytest.mark.unit
def test_task_relation_create_requires_relation_type() -> None:
    """Omitting relation_type raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskRelationCreate(source_task_id=uuid4(), target_task_id=uuid4())  # type: ignore[call-arg]


@pytest.mark.unit
def test_task_relation_create_rejects_invalid_relation_type() -> None:
    """Invalid relation_type raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskRelationCreate(
            source_task_id=uuid4(),
            target_task_id=uuid4(),
            relation_type="depends_on",
        )


@pytest.mark.unit
def test_task_relation_create_rejects_invalid_provider() -> None:
    """Invalid provider raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskRelationCreate(
            source_task_id=uuid4(),
            target_task_id=uuid4(),
            relation_type="blocks",
            provider="jira",
        )


@pytest.mark.unit
def test_task_relation_create_all_relation_types() -> None:
    """Verify all four valid relation types are accepted."""
    for rt in ["parent_of", "blocks", "relates_to", "duplicates"]:
        data = TaskRelationCreate(
            source_task_id=uuid4(),
            target_task_id=uuid4(),
            relation_type=rt,
        )
        assert data.relation_type == rt


@pytest.mark.unit
def test_task_relation_update_partial() -> None:
    """TaskRelationUpdate with only relation_type set."""
    data = TaskRelationUpdate(relation_type="relates_to")
    assert data.relation_type == "relates_to"
    assert data.external_id is None
    assert data.external_url is None
    assert data.provider is None
    assert data.last_synced_at is None


@pytest.mark.unit
def test_task_relation_update_empty() -> None:
    """TaskRelationUpdate with no fields set."""
    data = TaskRelationUpdate()
    assert data.relation_type is None


@pytest.mark.unit
def test_task_relation_update_rejects_invalid_relation_type() -> None:
    """Invalid relation_type on update raises ValidationError."""
    with pytest.raises(ValidationError):
        TaskRelationUpdate(relation_type="depends_on")


@pytest.mark.unit
def test_task_relation_response_from_attributes() -> None:
    """Verify model_config has from_attributes=True."""
    assert TaskRelationResponse.model_config.get("from_attributes") is True


# --- Service tests ---


@pytest.mark.unit
def test_task_relation_service_model() -> None:
    """Verify TaskRelationService().model is TaskRelation."""
    service = TaskRelationService()
    assert service.model is TaskRelation
