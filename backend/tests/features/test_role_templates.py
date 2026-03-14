import pytest
from pydantic import ValidationError

from features.role_templates.models import RoleTemplate
from features.role_templates.schemas.input import RoleTemplateCreate, RoleTemplateUpdate
from features.role_templates.schemas.output import RoleTemplateResponse, RoleTemplateSummary
from features.role_templates.service import RoleTemplateService


@pytest.mark.unit
def test_role_template_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(RoleTemplate, "name")
    assert hasattr(RoleTemplate, "source")
    assert hasattr(RoleTemplate, "archetype")
    assert hasattr(RoleTemplate, "default_model")
    assert hasattr(RoleTemplate, "persona")
    assert hasattr(RoleTemplate, "judgments")
    assert hasattr(RoleTemplate, "responsibilities")
    assert hasattr(RoleTemplate, "description")
    assert hasattr(RoleTemplate, "is_active")


@pytest.mark.unit
def test_role_template_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert RoleTemplate.Pattern.entity == "role_template"
    assert RoleTemplate.Pattern.reference_prefix == "ROLE"
    assert RoleTemplate.Pattern.track_changes is True


@pytest.mark.unit
def test_role_template_create_schema_defaults() -> None:
    """Verify default values via create schema."""
    data = RoleTemplateCreate(name="defaults-test")
    assert data.source == "custom"
    assert data.is_active is True
    assert data.persona == {}
    assert data.judgments == []
    assert data.responsibilities == []


@pytest.mark.unit
def test_role_template_create_schema() -> None:
    """Verify create schema with minimal data."""
    data = RoleTemplateCreate(name="test-role")
    assert data.name == "test-role"
    assert data.source == "custom"
    assert data.persona == {}
    assert data.judgments == []
    assert data.responsibilities == []
    assert data.is_active is True


@pytest.mark.unit
def test_role_template_create_schema_full() -> None:
    """Verify create schema with all fields."""
    data = RoleTemplateCreate(
        name="test-role",
        source="library",
        archetype="Analyst",
        default_model="claude-sonnet-4-20250514",
        persona={"traits": ["analytical"]},
        judgments=["judgment-1"],
        responsibilities=["resp-1"],
        description="A test role.",
        is_active=False,
    )
    assert data.name == "test-role"
    assert data.source == "library"
    assert data.archetype == "Analyst"
    assert data.persona == {"traits": ["analytical"]}
    assert data.judgments == ["judgment-1"]
    assert data.responsibilities == ["resp-1"]
    assert data.is_active is False


@pytest.mark.unit
def test_role_template_create_requires_name() -> None:
    """Verify name is required."""
    with pytest.raises(ValidationError):
        RoleTemplateCreate()  # type: ignore[call-arg]


@pytest.mark.unit
def test_role_template_create_rejects_empty_name() -> None:
    """Verify empty name is rejected."""
    with pytest.raises(ValidationError):
        RoleTemplateCreate(name="")


@pytest.mark.unit
def test_role_template_update_schema() -> None:
    """Verify update schema allows partial updates."""
    data = RoleTemplateUpdate(is_active=False)
    assert data.is_active is False
    assert data.name is None
    assert data.source is None


@pytest.mark.unit
def test_role_template_response_schema() -> None:
    """Verify response schema from_attributes config."""
    assert RoleTemplateResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_role_template_summary_schema() -> None:
    """Verify summary schema from_attributes config."""
    assert RoleTemplateSummary.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_role_template_service_model() -> None:
    """Verify service is configured with correct model."""
    service = RoleTemplateService()
    assert service.model is RoleTemplate
