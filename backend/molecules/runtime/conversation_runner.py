"""ConversationRunner — bridges stack-bench DB with agentic-patterns runtime.

Loads conversation history from DB, assembles an agent via AgentFactory,
calls the runner with streaming, and yields SSE events. Persists messages
and token counts back to DB after the stream completes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator

from agentic_patterns.core.systems.core.events import MessageCompleteEvent
from agentic_patterns.core.systems.streaming import SSEFormatter

from molecules.agents.assembler import AgentAssembler
from molecules.entities.conversation_entity import ConversationEntity
from molecules.runtime.agent_factory import AgentFactory

if TYPE_CHECKING:
    from uuid import UUID

    from agentic_patterns.core.systems.runners.base import RunnerProtocol
    from sqlalchemy.ext.asyncio import AsyncSession


class ConversationRunner:
    """Molecule that bridges DB conversations with agentic-patterns execution.

    Responsibilities:
    - Load conversation + message history from DB
    - Assemble agent via AgentFactory
    - Stream execution through a runner
    - Yield SSE-formatted events
    - Persist user message, assistant response, and token counts to DB
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.entity = ConversationEntity(db)
        self.assembler = AgentAssembler(db)

    async def send(
        self,
        conversation_id: UUID,
        message: str,
        *,
        agent_runner: RunnerProtocol | None = None,
    ) -> AsyncIterator[str]:
        """Send a message and stream SSE events.

        Args:
            conversation_id: UUID of the conversation
            message: User message text
            agent_runner: Runner to use (injectable for testing).
                         If None, creates a default Claude runner.

        Yields:
            SSE-formatted strings for each stream event.
        """
        # 1. Load conversation and validate
        conv = await self.entity.get_conversation(conversation_id)

        # 2. Load full history from DB
        data = await self.entity.get_with_messages(conversation_id)
        db_messages = data["messages"]

        # 3. Build message history for the runner
        message_history = self._build_message_history(db_messages)

        # 4. Assemble agent from DB config
        config = await self.assembler.assemble(conv.agent_name, model_override=conv.model)
        agent = AgentFactory.create(config)

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

            history.append({
                "kind": msg.kind,
                "parts": converted_parts,
            })

        return history

    async def _handle_error(self, conversation_id: UUID, error: Exception) -> None:
        """Handle an error during streaming by updating conversation state.

        Args:
            conversation_id: UUID of the conversation
            error: The exception that occurred
        """
        conv = await self.entity.get_conversation(conversation_id)
        if conv.state in ("created", "active"):
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
            A Claude API runner instance.
        """
        from agentic_patterns.core.systems.runners.claude_api import ClaudeRunner

        return ClaudeRunner()
