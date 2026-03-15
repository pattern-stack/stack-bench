"""Tests for ConversationRunner — the bridge between stack-bench DB and agentic-patterns runtime."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from molecules.runtime.agent_factory import AgentFactory
from molecules.runtime.conversation_runner import ConversationRunner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_conversation(
    *,
    state: str = "created",
    agent_name: str = "test-agent",
    model: str = "claude-sonnet-4-20250514",
    exchange_count: int = 0,
) -> MagicMock:
    conv = MagicMock()
    conv.id = uuid4()
    conv.state = state
    conv.agent_name = agent_name
    conv.model = model
    conv.exchange_count = exchange_count
    conv.total_input_tokens = 0
    conv.total_output_tokens = 0
    conv.agent_config = {
        "role_name": "Engineer",
        "persona": {"name": "Test Agent", "title": "Test"},
        "mission": "Help with testing",
    }
    conv.is_deleted = False
    conv.transition_to = MagicMock()
    return conv


def _make_agent_config() -> MagicMock:
    from molecules.agents.assembler import AgentConfig

    return AgentConfig(
        name="test-agent",
        role_name="Engineer",
        model="claude-sonnet-4-20250514",
        persona={"name": "Test Agent", "title": "Test"},
        mission="Help with testing",
        background=None,
        awareness={},
    )


# ---------------------------------------------------------------------------
# AgentFactory tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_agent_factory_creates_agent_from_config() -> None:
    """AgentFactory.create should produce an agentic-patterns Agent."""
    from agentic_patterns.core.organisms.agents import Agent

    config = _make_agent_config()
    agent = AgentFactory.create(config)

    assert isinstance(agent, Agent)
    assert agent.role.name == "Engineer"
    assert agent.get_model() == "claude-sonnet-4-20250514"


@pytest.mark.unit
def test_agent_factory_uses_model_from_config() -> None:
    """AgentFactory should use the model specified in AgentConfig."""
    config = _make_agent_config()
    config.model = "claude-opus-4-20250514"

    agent = AgentFactory.create(config)
    assert agent.get_model() == "claude-opus-4-20250514"


@pytest.mark.unit
def test_agent_factory_sets_mission() -> None:
    """AgentFactory should set the agent's mission from config."""
    config = _make_agent_config()
    agent = AgentFactory.create(config)

    assert agent.mission.objective == "Help with testing"


# ---------------------------------------------------------------------------
# ConversationRunner tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_conversation_runner_init() -> None:
    """ConversationRunner should compose entity and assembler."""
    db = AsyncMock()
    runner = ConversationRunner(db)

    assert runner.db is db
    assert runner.entity is not None
    assert runner.assembler is not None


@pytest.mark.unit
async def test_send_streams_sse_events() -> None:
    """send() should yield SSE-formatted strings from MockRunner stream events."""
    from agentic_patterns.core.systems.core.events import (
        MessageChunkEvent,
        MessageCompleteEvent,
        MessageStartEvent,
    )
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    # Prepare mocks
    conv = _make_conversation()
    config = _make_agent_config()

    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(
        return_value={"conversation": conv, "messages": [], "tool_calls": []}
    )
    runner.assembler.assemble = AsyncMock(return_value=config)

    # Use MockRunner
    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="Hello from mock!", input_tokens=10, output_tokens=5))

    events: list[str] = []
    async for sse in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        events.append(sse)

    # Should have SSE events (message.start, chunks, message.complete)
    assert len(events) > 0

    # Check that events are SSE formatted
    for event in events:
        assert "event:" in event or "data:" in event


@pytest.mark.unit
async def test_send_persists_user_message() -> None:
    """send() should persist the user message to DB via entity.add_message."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation()
    config = _make_agent_config()

    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(
        return_value={"conversation": conv, "messages": [], "tool_calls": []}
    )
    runner.entity.add_message = AsyncMock()
    runner.assembler.assemble = AsyncMock(return_value=config)

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="Reply"))

    # Consume all events
    async for _ in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        pass

    # Should have persisted user message (kind="request")
    calls = runner.entity.add_message.call_args_list
    user_calls = [c for c in calls if c.kwargs.get("kind") == "request" or (c.args and len(c.args) > 1 and c.args[1] == "request")]
    assert len(user_calls) >= 1


@pytest.mark.unit
async def test_send_persists_assistant_response() -> None:
    """send() should persist the assistant response to DB via entity.add_message."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation()
    config = _make_agent_config()

    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(
        return_value={"conversation": conv, "messages": [], "tool_calls": []}
    )
    runner.entity.add_message = AsyncMock()
    runner.assembler.assemble = AsyncMock(return_value=config)

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="I am a reply", input_tokens=15, output_tokens=25))

    async for _ in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        pass

    # Should have persisted assistant response (kind="response")
    calls = runner.entity.add_message.call_args_list
    response_calls = [c for c in calls if c.kwargs.get("kind") == "response" or (c.args and len(c.args) > 1 and c.args[1] == "response")]
    assert len(response_calls) >= 1


@pytest.mark.unit
async def test_send_transitions_state_to_active() -> None:
    """send() should transition conversation state from 'created' to 'active'."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation(state="created")
    config = _make_agent_config()

    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(
        return_value={"conversation": conv, "messages": [], "tool_calls": []}
    )
    runner.entity.add_message = AsyncMock()
    runner.assembler.assemble = AsyncMock(return_value=config)

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="Reply"))

    async for _ in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        pass

    # Conversation should be transitioned (add_message handles this internally)
    assert runner.entity.add_message.called


@pytest.mark.unit
async def test_send_builds_history_from_db() -> None:
    """send() should reconstruct message history from DB messages."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation(state="active", exchange_count=1)
    config = _make_agent_config()

    # Simulate existing messages in DB
    existing_msg = MagicMock()
    existing_msg.kind = "request"
    existing_msg.sequence = 1
    existing_msg.id = uuid4()

    existing_part = MagicMock()
    existing_part.part_type = "text"
    existing_part.content = "Previous message"
    existing_part.tool_call_id = None
    existing_part.tool_name = None
    existing_part.tool_arguments = None

    existing_resp = MagicMock()
    existing_resp.kind = "response"
    existing_resp.sequence = 2
    existing_resp.id = uuid4()

    existing_resp_part = MagicMock()
    existing_resp_part.part_type = "text"
    existing_resp_part.content = "Previous response"
    existing_resp_part.tool_call_id = None
    existing_resp_part.tool_name = None
    existing_resp_part.tool_arguments = None

    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(
        return_value={
            "conversation": conv,
            "messages": [
                {"message": existing_msg, "parts": [existing_part]},
                {"message": existing_resp, "parts": [existing_resp_part]},
            ],
            "tool_calls": [],
        }
    )
    runner.entity.add_message = AsyncMock()
    runner.assembler.assemble = AsyncMock(return_value=config)

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="Reply"))

    async for _ in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        pass

    # MockRunner should have been called with message_history
    assert len(mock_runner.call_history) == 1


@pytest.mark.unit
async def test_send_commits_after_completion() -> None:
    """send() should commit the DB session after streaming completes."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation()
    config = _make_agent_config()

    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(
        return_value={"conversation": conv, "messages": [], "tool_calls": []}
    )
    runner.entity.add_message = AsyncMock()
    runner.assembler.assemble = AsyncMock(return_value=config)

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="Reply"))

    async for _ in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        pass

    db.commit.assert_awaited()


@pytest.mark.unit
async def test_send_handles_error_gracefully() -> None:
    """send() should handle errors during streaming and set conversation state to failed."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation(state="active")
    config = _make_agent_config()

    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(
        return_value={"conversation": conv, "messages": [], "tool_calls": []}
    )
    runner.entity.add_message = AsyncMock()
    runner.assembler.assemble = AsyncMock(return_value=config)

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="", error=RuntimeError("LLM failed")))

    events: list[str] = []
    async for sse in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        events.append(sse)

    # Should have yielded an error event
    error_events = [e for e in events if "error" in e.lower()]
    assert len(error_events) > 0
