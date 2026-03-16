"""ConversationRunner — bridges stack-bench DB with agentic-patterns runtime.

Loads conversation history from DB, assembles an agent via AgentFactory,
calls the runner with streaming, and yields SSE events. Persists messages,
tool calls, and token counts back to DB after the stream completes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agentic_patterns.core.systems.core.events import (
    MessageCompleteEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from agentic_patterns.core.systems.streaming import SSEFormatter

from features.tool_calls.schemas.input import ToolCallCreate, ToolCallUpdate
from molecules.entities.conversation_entity import ConversationEntity


if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

    from agentic_patterns.core.systems.runners.base import RunnerProtocol
    from sqlalchemy.ext.asyncio import AsyncSession


class ConversationRunner:
    # TODO: This will become the inner loop of an ADR-001 AgentNode
    """Molecule that bridges DB conversations with agentic-patterns execution.

    Responsibilities:
    - Load conversation + message history from DB
    - Assemble agent via AgentFactory
    - Stream execution through a runner
    - Yield SSE-formatted events
    - Persist user message, assistant response, tool calls, and token counts to DB
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.entity = ConversationEntity(db)

    async def send(
        self,
        conversation_id: UUID,
        message: str,
        *,
        working_directory: str | None = None,
        agent_runner: RunnerProtocol | None = None,
    ) -> AsyncIterator[str]:
        """Send a message and stream SSE events.

        Args:
            conversation_id: UUID of the conversation
            message: User message text
            working_directory: Optional working directory for tool execution.
                              Stored in the conversation's metadata_ dict.
            agent_runner: Runner to use (injectable for testing).
                         If None, creates a default Claude runner.

        Yields:
            SSE-formatted strings for each stream event.
        """
        # 1. Load conversation and validate
        conv = await self.entity.get_conversation(conversation_id)

        # Store working_directory in conversation metadata if provided
        if working_directory is not None:
            metadata = conv.metadata_ or {}
            metadata["working_directory"] = working_directory
            conv.metadata_ = metadata
            await self.db.flush()

        # 2. Load full history from DB
        data = await self.entity.get_with_messages(conversation_id)
        db_messages = data["messages"]

        # 3. Build message history for the runner
        message_history = self._build_message_history(db_messages)

        # 4. Assemble agent from DB config
        agent = await self.entity.assembler.build_agent(conv.agent_name, model_override=conv.model)

        # 5. Determine next sequence number
        next_sequence = len(db_messages) + 1

        # 6. Persist user message
        await self.entity.add_message(
            conversation_id=conversation_id,
            kind="request",
            sequence=next_sequence,
            parts=[{"type": "text", "content": message}],
        )

        # 7. Get or create runner
        runner = agent_runner or self._get_default_runner()

        # 8. Stream and yield SSE events, collecting response data
        formatter = SSEFormatter()
        full_response = ""
        input_tokens = 0
        output_tokens = 0
        pending_tool_calls: dict[str, Any] = {}  # tool_call_id -> ToolCall record

        try:
            async for event in runner.run_stream(
                agent,
                message,
                message_history=message_history,
            ):
                # Yield SSE-formatted event
                yield formatter.format_stream_event(event)

                # Collect response data from MessageCompleteEvent
                if isinstance(event, MessageCompleteEvent):
                    full_response = event.content
                    input_tokens = event.input_tokens
                    output_tokens = event.output_tokens

                # Persist tool call start
                elif isinstance(event, ToolCallStartEvent):
                    tc = await self.entity.tool_call_service.create(
                        self.db,
                        ToolCallCreate(
                            conversation_id=conversation_id,
                            tool_call_id=event.tool_call_id,
                            tool_name=event.tool_name,
                            arguments=event.arguments or None,
                        ),
                    )
                    pending_tool_calls[event.tool_call_id] = tc

                # Persist tool call result
                elif isinstance(event, ToolCallEndEvent):
                    tc = pending_tool_calls.get(event.tool_call_id)
                    if tc is not None:
                        new_state = "failed" if event.error else "executed"
                        tc.transition_to(new_state)
                        await self.entity.tool_call_service.update(
                            self.db,
                            tc.id,
                            ToolCallUpdate(
                                result=str(event.result) if event.result is not None else None,
                                error=event.error,
                                duration_ms=event.duration_ms,
                            ),
                        )

        except Exception as e:
            # Yield error as SSE event
            error_data = {
                "error_type": type(e).__name__,
                "message": str(e),
            }
            yield formatter.format("error", error_data)

            # Persist error state
            await self._handle_error(conversation_id, e)
            await self.db.commit()
            return

        # 9. Persist assistant response
        await self.entity.add_message(
            conversation_id=conversation_id,
            kind="response",
            sequence=next_sequence + 1,
            parts=[{"type": "text", "content": full_response}],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # 10. Commit all changes
        await self.db.commit()

    def _build_message_history(
        self,
        db_messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert DB message records to runner-compatible message history.

        Args:
            db_messages: List of {message: Message, parts: [MessagePart, ...]}

        Returns:
            List of dicts in the format expected by runner.run_stream(message_history=...)
        """
        history: list[dict[str, Any]] = []
        for msg_data in db_messages:
            msg = msg_data["message"]
            parts = msg_data["parts"]

            converted_parts: list[dict[str, Any]] = []
            for part in parts:
                part_dict: dict[str, Any] = {
                    "type": part.part_type,
                    "content": part.content,
                }
                if part.tool_call_id:
                    part_dict["tool_call_id"] = part.tool_call_id
                if part.tool_name:
                    part_dict["tool_name"] = part.tool_name
                if part.tool_arguments:
                    part_dict["arguments"] = part.tool_arguments
                converted_parts.append(part_dict)

            history.append(
                {
                    "kind": msg.kind,
                    "parts": converted_parts,
                }
            )

        return history

    async def _handle_error(self, conversation_id: UUID, error: Exception) -> None:
        """Handle an error during streaming by updating conversation state.

        Args:
            conversation_id: UUID of the conversation
            error: The exception that occurred
        """
        conv = await self.entity.get_conversation(conversation_id)
        if conv.state in ("created", "active"):
            # TODO: Use transition_through() when available in pattern-stack
            try:
                if conv.state == "created":
                    conv.transition_to("active")
                conv.transition_to("failed")
                conv.error_message = str(error)
                await self.db.flush()
            except Exception:
                # If state transition fails, just log and continue
                pass

    def _get_default_runner(self) -> RunnerProtocol:
        """Get the default runner for production use.

        Returns:
            An AgentRunner instance (uses LiteLLM under the hood).
        """
        # TODO: Use RunnerPool for phase-based runner selection
        from agentic_patterns.core.systems.runners.agent import AgentRunner

        return AgentRunner()
