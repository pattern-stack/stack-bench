from uuid import uuid4

import pytest
from pydantic import ValidationError

from features.agent_definitions.models import AgentDefinition
from features.agent_definitions.schemas.input import AgentDefinitionCreate, AgentDefinitionUpdate
from features.agent_definitions.schemas.output import AgentDefinitionResponse, AgentDefinitionSummary
from features.agent_definitions.service import AgentDefinitionService


@pytest.mark.unit
def test_agent_definition_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(AgentDefinition, "name")
    assert hasattr(AgentDefinition, "role_template_id")
    assert hasattr(AgentDefinition, "model_override")
    assert hasattr(AgentDefinition, "mission")
    assert hasattr(AgentDefinition, "background")
    assert hasattr(AgentDefinition, "awareness")
    assert hasattr(AgentDefinition, "is_active")


@pytest.mark.unit
def test_agent_definition_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert AgentDefinition.Pattern.entity == "agent_definition"
    assert AgentDefinition.Pattern.reference_prefix == "AGNT"
    assert AgentDefinition.Pattern.track_changes is True


@pytest.mark.unit
def test_agent_definition_create_schema_defaults() -> None:
    """Verify default values via create schema."""
    data = AgentDefinitionCreate(
        name="defaults-test",
        role_template_id=uuid4(),
        mission="Test mission",
    )
    assert data.is_active is True
    assert data.awareness == {}


@pytest.mark.unit
def test_agent_definition_create_schema() -> None:
    """Verify create schema with minimal data."""
    role_id = uuid4()
    data = AgentDefinitionCreate(
        name="test-agent",
        role_template_id=role_id,
        mission="Test mission",
    )
    assert data.name == "test-agent"
    assert data.role_template_id == role_id
    assert data.mission == "Test mission"
    assert data.is_active is True
    assert data.awareness == {}


@pytest.mark.unit
def test_agent_definition_create_schema_full() -> None:
    """Verify create schema with all fields."""
    role_id = uuid4()
    data = AgentDefinitionCreate(
        name="test-agent",
        role_template_id=role_id,
        model_override="claude-opus-4-20250514",
        mission="Test mission",
        background="Expert developer.",
        awareness={"key": "value"},
        is_active=False,
    )
    assert data.name == "test-agent"
    assert data.model_override == "claude-opus-4-20250514"
    assert data.background == "Expert developer."
    assert data.awareness == {"key": "value"}
    assert data.is_active is False


@pytest.mark.unit
def test_agent_definition_create_requires_name() -> None:
    """Verify name is required."""
    with pytest.raises(ValidationError):
        AgentDefinitionCreate(role_template_id=uuid4(), mission="Test")  # type: ignore[call-arg]


@pytest.mark.unit
def test_agent_definition_create_requires_role_template_id() -> None:
    """Verify role_template_id is required."""
    with pytest.raises(ValidationError):
        AgentDefinitionCreate(name="test", mission="Test")  # type: ignore[call-arg]


@pytest.mark.unit
def test_agent_definition_create_requires_mission() -> None:
    """Verify mission is required."""
    with pytest.raises(ValidationError):
        AgentDefinitionCreate(name="test", role_template_id=uuid4())  # type: ignore[call-arg]


@pytest.mark.unit
def test_agent_definition_create_rejects_empty_name() -> None:
    """Verify empty name is rejected."""
    with pytest.raises(ValidationError):
        AgentDefinitionCreate(name="", role_template_id=uuid4(), mission="Test")


@pytest.mark.unit
def test_agent_definition_create_rejects_empty_mission() -> None:
    """Verify empty mission is rejected."""
    with pytest.raises(ValidationError):
        AgentDefinitionCreate(name="test", role_template_id=uuid4(), mission="")


@pytest.mark.unit
def test_agent_definition_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = AgentDefinitionUpdate(is_active=False)
    assert data.is_active is False
    assert data.name is None
    assert data.mission is None


@pytest.mark.unit
def test_agent_definition_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert AgentDefinitionResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_agent_definition_summary_schema() -> None:
    """Verify summary schema from_attributes config."""
    assert AgentDefinitionSummary.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_agent_definition_service_model() -> None:
    """Verify service is configured with correct model."""
    service = AgentDefinitionService()
    assert service.model is AgentDefinition
