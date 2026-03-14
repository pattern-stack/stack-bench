import pytest


@pytest.mark.unit
def test_seed_specs_importable() -> None:
    """Verify seed specs can be imported."""
    from seeds.specs import AgentDefinitionSeed, RoleTemplateSeed

    assert RoleTemplateSeed.entity_type == "RoleTemplate"
    assert AgentDefinitionSeed.entity_type == "AgentDefinition"


@pytest.mark.unit
def test_seed_specs_registered() -> None:
    """Verify seed specs are registered with the YAML loader."""
    import seeds  # noqa: F401 — triggers register_spec calls

    from pattern_stack.atoms.seeding.loaders.yaml_loader import get_registered_specs

    specs = get_registered_specs()
    assert "role_templates" in specs
    assert "agent_definitions" in specs
