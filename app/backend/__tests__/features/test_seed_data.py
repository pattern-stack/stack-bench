from pathlib import Path

import pytest
import yaml


@pytest.mark.unit
def test_seed_yaml_loadable() -> None:
    """Verify seed YAML loads with expected structure."""
    seed_path = Path(__file__).parent.parent.parent / "src" / "seeds" / "agents.yaml"
    with open(seed_path) as f:
        data = yaml.safe_load(f)
    assert len(data["role_templates"]) == 5
    assert len(data["agent_definitions"]) == 5
    names = {rt["name"] for rt in data["role_templates"]}
    assert names == {"understander", "planner", "specifier", "implementer", "reviewer"}


@pytest.mark.unit
def test_seed_agent_definitions_reference_valid_roles() -> None:
    """Verify each agent definition references an existing role template."""
    seed_path = Path(__file__).parent.parent.parent / "src" / "seeds" / "agents.yaml"
    with open(seed_path) as f:
        data = yaml.safe_load(f)
    role_names = {rt["name"] for rt in data["role_templates"]}
    for ad in data["agent_definitions"]:
        assert ad["role_template"] in role_names, (
            f"Agent '{ad['name']}' references unknown role '{ad['role_template']}'"
        )


@pytest.mark.unit
def test_seed_role_templates_have_required_fields() -> None:
    """Verify each role template has required fields."""
    seed_path = Path(__file__).parent.parent.parent / "src" / "seeds" / "agents.yaml"
    with open(seed_path) as f:
        data = yaml.safe_load(f)
    for rt in data["role_templates"]:
        assert "name" in rt
        assert "source" in rt
        assert "responsibilities" in rt
        assert len(rt["responsibilities"]) > 0


@pytest.mark.unit
def test_seed_agent_definitions_have_required_fields() -> None:
    """Verify each agent definition has required fields."""
    seed_path = Path(__file__).parent.parent.parent / "src" / "seeds" / "agents.yaml"
    with open(seed_path) as f:
        data = yaml.safe_load(f)
    for ad in data["agent_definitions"]:
        assert "name" in ad
        assert "role_template" in ad
        assert "mission" in ad
        assert len(ad["mission"]) > 0
