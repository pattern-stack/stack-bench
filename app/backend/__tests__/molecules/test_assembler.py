from unittest.mock import AsyncMock

import pytest

from molecules.agents.assembler import AgentAssembler, AgentConfig


@pytest.mark.unit
def test_agent_config_fields() -> None:
    """AgentConfig dataclass holds all expected fields."""
    config = AgentConfig(
        name="test",
        role_name="tester",
        model="claude-sonnet-4-20250514",
        persona={"tone": "friendly"},
        mission="test things",
        background=None,
        awareness={"context": True},
    )
    assert config.name == "test"
    assert config.role_name == "tester"
    assert config.model == "claude-sonnet-4-20250514"
    assert config.persona == {"tone": "friendly"}
    assert config.mission == "test things"
    assert config.background is None
    assert config.awareness == {"context": True}


@pytest.mark.unit
def test_agent_config_with_background() -> None:
    """AgentConfig can hold a background string."""
    config = AgentConfig(
        name="dev",
        role_name="developer",
        model="claude-opus-4-20250514",
        persona={},
        mission="build",
        background="Senior engineer",
        awareness={},
    )
    assert config.background == "Senior engineer"


@pytest.mark.unit
def test_assembler_init() -> None:
    """AgentAssembler composes role and agent services."""
    db = AsyncMock()
    assembler = AgentAssembler(db)
    assert assembler.db is db
    assert assembler._role_service is not None
    assert assembler._agent_service is not None
