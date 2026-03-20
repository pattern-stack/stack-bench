from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from molecules.apis.conversation_api import (
    AgentDetailResponse,
    ConversationAPI,
    ConversationDetailResponse,
)


@pytest.mark.unit
def test_conversation_detail_response_schema() -> None:
    """ConversationDetailResponse holds full conversation data."""
    now = datetime.now(UTC)
    resp = ConversationDetailResponse(
        id=uuid4(),
        agent_name="test",
        model="claude-sonnet-4-20250514",
        state="created",
        exchange_count=0,
        total_input_tokens=0,
        total_output_tokens=0,
        messages=[],
        tool_calls=[],
        created_at=now,
        updated_at=now,
    )
    assert resp.state == "created"
    assert resp.messages == []
    assert resp.tool_calls == []


@pytest.mark.unit
def test_conversation_detail_response_with_data() -> None:
    """ConversationDetailResponse accepts message and tool_call dicts."""
    now = datetime.now(UTC)
    resp = ConversationDetailResponse(
        id=uuid4(),
        agent_name="understander",
        model="claude-sonnet-4-20250514",
        state="active",
        exchange_count=3,
        total_input_tokens=1000,
        total_output_tokens=500,
        messages=[{"id": "abc", "kind": "request", "sequence": 0, "parts": []}],
        tool_calls=[{"id": "tc1", "tool_name": "read", "state": "executed"}],
        created_at=now,
        updated_at=now,
    )
    assert resp.exchange_count == 3
    assert len(resp.messages) == 1
    assert len(resp.tool_calls) == 1


@pytest.mark.unit
def test_conversation_detail_response_from_attributes() -> None:
    """ConversationDetailResponse supports from_attributes."""
    assert ConversationDetailResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_agent_detail_response_schema() -> None:
    """AgentDetailResponse holds agent configuration."""
    resp = AgentDetailResponse(
        name="understander",
        role_name="understander",
        model="claude-sonnet-4-20250514",
        mission="Analyze tasks",
    )
    assert resp.name == "understander"
    assert resp.background is None


@pytest.mark.unit
def test_agent_detail_response_with_background() -> None:
    """AgentDetailResponse can include background."""
    resp = AgentDetailResponse(
        name="developer",
        role_name="developer",
        model="claude-opus-4-20250514",
        mission="Write code",
        background="Senior engineer with 10 years experience",
    )
    assert resp.background == "Senior engineer with 10 years experience"


@pytest.mark.unit
def test_agent_detail_response_from_attributes() -> None:
    """AgentDetailResponse supports from_attributes."""
    assert AgentDetailResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_conversation_api_init() -> None:
    """ConversationAPI composes entity and assembler."""
    db = AsyncMock()
    api = ConversationAPI(db)
    assert api.db is db
    assert api.entity is not None
    assert api.assembler is not None
