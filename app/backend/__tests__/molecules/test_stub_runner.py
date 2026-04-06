"""Tests for StubRunner — echo-based RunnerProtocol for development."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from molecules.runtime.stub_runner import StubRunner


@pytest.mark.unit
def test_stub_runner_returns_async_iterator_synchronously() -> None:
    """run_stream should return an async iterator without being awaited."""
    runner = StubRunner()
    agent = MagicMock()
    agent.get_model.return_value = "stub"

    result = runner.run_stream(agent, "Hello")

    # Should be an async iterator, not a coroutine
    assert hasattr(result, "__aiter__")
    assert hasattr(result, "__anext__")


@pytest.mark.unit
async def test_stub_runner_yields_message_events() -> None:
    """run_stream should yield reasoning, chunk, and complete events."""
    from agentic_patterns.core.systems.core.events import (
        MessageChunkEvent,
        MessageCompleteEvent,
        ReasoningEvent,
    )

    runner = StubRunner()
    agent = MagicMock()
    agent.get_model.return_value = "stub"

    events = []
    async for event in runner.run_stream(agent, "Hello world"):
        events.append(event)

    # Should have at least a reasoning event, a chunk, and a complete event
    event_types = [type(e) for e in events]
    assert ReasoningEvent in event_types
    assert MessageChunkEvent in event_types
    assert MessageCompleteEvent in event_types


@pytest.mark.unit
async def test_stub_runner_echoes_message() -> None:
    """run_stream should echo the input message in the response."""
    from agentic_patterns.core.systems.core.events import (
        MessageChunkEvent,
        MessageCompleteEvent,
    )

    runner = StubRunner()
    agent = MagicMock()
    agent.get_model.return_value = "stub"

    events = []
    async for event in runner.run_stream(agent, "Test echo"):
        events.append(event)

    # The chunk should contain the echoed message
    chunks = [e for e in events if isinstance(e, MessageChunkEvent)]
    assert any("Test echo" in c.delta for c in chunks)

    # The complete event should have the full echoed content
    completes = [e for e in events if isinstance(e, MessageCompleteEvent)]
    assert len(completes) == 1
    assert "Test echo" in completes[0].content


@pytest.mark.unit
async def test_stub_runner_reports_zero_tokens() -> None:
    """StubRunner should report zero token usage."""
    from agentic_patterns.core.systems.core.events import MessageCompleteEvent

    runner = StubRunner()
    agent = MagicMock()
    agent.get_model.return_value = "stub"

    events = []
    async for event in runner.run_stream(agent, "Hi"):
        events.append(event)

    completes = [e for e in events if isinstance(e, MessageCompleteEvent)]
    assert completes[0].input_tokens == 0
    assert completes[0].output_tokens == 0


@pytest.mark.unit
async def test_stub_runner_accepts_all_protocol_kwargs() -> None:
    """run_stream should accept all RunnerProtocol keyword arguments."""
    runner = StubRunner()
    agent = MagicMock()
    agent.get_model.return_value = "stub"

    # Should not raise with all kwargs
    events = []
    async for event in runner.run_stream(
        agent,
        "Hello",
        message_history=[{"kind": "request", "parts": []}],
        tool_executor=MagicMock(),
        hooks=MagicMock(),
        event_bus=MagicMock(),
        max_iterations=5,
        trace_id="trace-123",
        parent_span_id="span-456",
    ):
        events.append(event)

    assert len(events) > 0


@pytest.mark.unit
async def test_stub_runner_works_with_conversation_runner() -> None:
    """StubRunner should produce valid SSE when used through ConversationRunner."""
    from unittest.mock import AsyncMock

    from molecules.runtime.conversation_runner import ConversationRunner

    db = AsyncMock()
    runner = ConversationRunner(db)

    conv = MagicMock()
    conv.id = MagicMock()
    conv.state = "created"
    conv.agent_name = "orchestrator"
    conv.model = "stub"
    conv.exchange_count = 0
    conv.total_input_tokens = 0
    conv.total_output_tokens = 0
    conv.agent_config = {}
    conv.is_deleted = False
    conv.transition_to = MagicMock()

    runner.entity.get_conversation = AsyncMock(return_value=conv)
    runner.entity.get_with_messages = AsyncMock(return_value={"conversation": conv, "messages": [], "tool_calls": []})
    runner.entity.add_message = AsyncMock()
    runner.entity.assembler.build_agent = AsyncMock(return_value=MagicMock())

    stub = StubRunner()
    events = []
    async for sse in runner.send(conv.id, "Hello", agent_runner=stub):
        events.append(sse)

    # Should have SSE-formatted events
    assert len(events) > 0
    for event in events:
        assert "event:" in event or "data:" in event
