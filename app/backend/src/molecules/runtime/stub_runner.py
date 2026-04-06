"""StubRunner — echo-based RunnerProtocol for development/testing.

Returns echoed messages without calling any LLM API. Used when
ANTHROPIC_API_KEY is not configured, proving the full streaming
pipeline end-to-end.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agentic_patterns.core.systems.core.events import (
    MessageChunkEvent,
    MessageCompleteEvent,
    ReasoningEvent,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from agentic_patterns.core.systems.streaming import StreamEvent


class StubRunner:
    """Echo runner for development/testing when no API key is available."""

    def run_stream(
        self,
        agent: Any,
        message: str,
        *,
        message_history: list[dict[str, Any]] | None = None,
        tool_executor: Any | None = None,
        hooks: Any | None = None,
        event_bus: Any | None = None,
        max_iterations: int = 10,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Return an async iterator of stream events that echo the input message.

        Note: This method is NOT async — it returns an async iterator
        synchronously, matching RunnerProtocol's actual signature.
        """

        async def _generate() -> AsyncIterator[StreamEvent]:
            yield ReasoningEvent(content="Processing request...")
            yield MessageChunkEvent(delta=f"Echo: {message}")
            yield MessageCompleteEvent(
                content=f"Echo: {message}",
                input_tokens=0,
                output_tokens=0,
            )

        return _generate()
