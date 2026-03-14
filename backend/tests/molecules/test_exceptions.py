from uuid import uuid4

import pytest

from molecules.exceptions import (
    AgentNotFoundError,
    ConversationNotFoundError,
    MoleculeError,
)


@pytest.mark.unit
def test_molecule_error_is_base_exception() -> None:
    """MoleculeError is the base for all molecule errors."""
    err = MoleculeError("test")
    assert isinstance(err, Exception)
    assert str(err) == "test"


@pytest.mark.unit
def test_conversation_not_found_error() -> None:
    """ConversationNotFoundError includes conversation_id and message."""
    cid = uuid4()
    err = ConversationNotFoundError(cid)
    assert "not found" in str(err)
    assert str(cid) in str(err)
    assert err.conversation_id == cid
    assert isinstance(err, MoleculeError)


@pytest.mark.unit
def test_agent_not_found_error_with_available() -> None:
    """AgentNotFoundError includes name and available list."""
    err = AgentNotFoundError("unknown", ["a", "b"])
    assert "unknown" in str(err)
    assert err.name == "unknown"
    assert err.available == ["a", "b"]
    assert isinstance(err, MoleculeError)


@pytest.mark.unit
def test_agent_not_found_error_no_available() -> None:
    """AgentNotFoundError works with no available agents."""
    err = AgentNotFoundError("missing")
    assert "missing" in str(err)
    assert err.available == []
    assert "(none)" in str(err)
