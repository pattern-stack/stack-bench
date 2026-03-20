"""Tests for ConversationRunner — the bridge between stack-bench DB and agentic-patterns runtime."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

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


# ---------------------------------------------------------------------------
# ConversationRunner tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_conversation_runner_init() -> None:
    """ConversationRunner should compose entity (which owns the assembler)."""
    db = AsyncMock()
    runner = ConversationRunner(db)

    assert runner.db is db
    assert runner.entity is not None
    assert runner.entity.assembler is not None


@pytest.mark.unit
async def test_send_streams_sse_events() -> None:
    """send() should yield SSE-formatted strings from MockRunner stream events."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    # Prepare mocks
    conv = _make_conversation()
    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(return_value={"conversation": conv, "messages": [], "tool_calls": []})
    runner.entity.assembler.build_agent = AsyncMock(return_value=MagicMock())

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
    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(return_value={"conversation": conv, "messages": [], "tool_calls": []})
    runner.entity.add_message = AsyncMock()
    runner.entity.assembler.build_agent = AsyncMock(return_value=MagicMock())

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="Reply"))

    # Consume all events
    async for _ in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        pass

    # Should have persisted user message (kind="request")
    calls = runner.entity.add_message.call_args_list
    user_calls = [
        c for c in calls if c.kwargs.get("kind") == "request" or (c.args and len(c.args) > 1 and c.args[1] == "request")
    ]
    assert len(user_calls) >= 1


@pytest.mark.unit
async def test_send_persists_assistant_response() -> None:
    """send() should persist the assistant response to DB via entity.add_message."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation()
    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(return_value={"conversation": conv, "messages": [], "tool_calls": []})
    runner.entity.add_message = AsyncMock()
    runner.entity.assembler.build_agent = AsyncMock(return_value=MagicMock())

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="I am a reply", input_tokens=15, output_tokens=25))

    async for _ in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        pass

    # Should have persisted assistant response (kind="response")
    calls = runner.entity.add_message.call_args_list
    response_calls = [
        c
        for c in calls
        if c.kwargs.get("kind") == "response" or (c.args and len(c.args) > 1 and c.args[1] == "response")
    ]
    assert len(response_calls) >= 1


@pytest.mark.unit
async def test_send_calls_add_message() -> None:
    """send() should call add_message for both user request and assistant response."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation(state="created")
    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(return_value={"conversation": conv, "messages": [], "tool_calls": []})
    runner.entity.add_message = AsyncMock()
    runner.entity.assembler.build_agent = AsyncMock(return_value=MagicMock())

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="Reply"))

    async for _ in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        pass

    # add_message should be called for both request and response
    assert runner.entity.add_message.call_count == 2


@pytest.mark.unit
async def test_send_builds_history_from_db() -> None:
    """send() should reconstruct message history from DB messages."""
    from agentic_patterns.core.systems.runners.mock import MockResponse, MockRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation(state="active", exchange_count=1)

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
    runner.entity.assembler.build_agent = AsyncMock(return_value=MagicMock())

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
    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(return_value={"conversation": conv, "messages": [], "tool_calls": []})
    runner.entity.add_message = AsyncMock()
    runner.entity.assembler.build_agent = AsyncMock(return_value=MagicMock())

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
    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(return_value={"conversation": conv, "messages": [], "tool_calls": []})
    runner.entity.add_message = AsyncMock()
    runner.entity.assembler.build_agent = AsyncMock(return_value=MagicMock())

    mock_runner = MockRunner()
    mock_runner.add_response("*", MockResponse(content="", error=RuntimeError("LLM failed")))

    events: list[str] = []
    async for sse in runner.send(conv.id, "Hello", agent_runner=mock_runner):
        events.append(sse)

    # Should have yielded an error event
    error_events = [e for e in events if "error" in e.lower()]
    assert len(error_events) > 0


@pytest.mark.unit
def test_build_message_history_with_tool_call_parts() -> None:
    """_build_message_history should include tool call fields when present on parts."""
    db = AsyncMock()
    runner = ConversationRunner(db)

    # Simulate a message with a tool-call part
    msg = MagicMock()
    msg.kind = "response"

    tool_part = MagicMock()
    tool_part.part_type = "tool_use"
    tool_part.content = None
    tool_part.tool_call_id = "call_abc123"
    tool_part.tool_name = "read_file"
    tool_part.tool_arguments = {"path": "/tmp/test.py"}

    result_part = MagicMock()
    result_part.part_type = "tool_result"
    result_part.content = "file contents here"
    result_part.tool_call_id = "call_abc123"
    result_part.tool_name = None
    result_part.tool_arguments = None

    history = runner._build_message_history(
        [
            {"message": msg, "parts": [tool_part, result_part]},
        ]
    )

    assert len(history) == 1
    parts = history[0]["parts"]
    assert len(parts) == 2

    # First part should have tool call fields
    assert parts[0]["tool_call_id"] == "call_abc123"
    assert parts[0]["tool_name"] == "read_file"
    assert parts[0]["arguments"] == {"path": "/tmp/test.py"}

    # Second part should have tool_call_id but not tool_name
    assert parts[1]["tool_call_id"] == "call_abc123"
    assert "tool_name" not in parts[1]
    assert "arguments" not in parts[1]


@pytest.mark.unit
async def test_handle_error_with_created_state() -> None:
    """_handle_error should transition created -> active -> failed."""
    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = _make_conversation(state="created")

    # Track state transitions
    transitions: list[str] = []
    original_state = "created"

    def mock_transition(new_state: str) -> None:
        nonlocal original_state
        transitions.append(new_state)
        conv.state = new_state

    conv.transition_to = MagicMock(side_effect=mock_transition)

    runner.entity.get_conversation = AsyncMock(return_value=conv)

    await runner._handle_error(conv.id, RuntimeError("test error"))

    # Should have transitioned through created -> active -> failed
    assert transitions == ["active", "failed"]
    assert conv.error_message == "test error"
    db.flush.assert_awaited()
