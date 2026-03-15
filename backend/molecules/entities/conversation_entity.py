from __future__ import annotations

from typing import TYPE_CHECKING, Any

from features.conversations.schemas.input import ConversationCreate, ConversationUpdate
from features.conversations.service import ConversationService
from features.message_parts.schemas.input import MessagePartCreate
from features.message_parts.service import MessagePartService
from features.messages.schemas.input import MessageCreate
from features.messages.service import MessageService
from features.tool_calls.service import ToolCallService
from molecules.agents.assembler import AgentAssembler, AgentConfig
from molecules.exceptions import ConversationNotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from features.conversations.models import Conversation
    from features.messages.models import Message


class ConversationEntity:
    """Domain aggregate for conversation lifecycle."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.conversation_service = ConversationService()
        self.message_service = MessageService()
        self.message_part_service = MessagePartService()
        self.tool_call_service = ToolCallService()
        self.assembler = AgentAssembler(db)

    async def create_conversation(
        self,
        agent_name: str,
        model: str | None = None,
    ) -> Conversation:
        """Create a new conversation with agent validation."""
        agent_config: AgentConfig = await self.assembler.assemble(agent_name, model_override=model)

        conv = await self.conversation_service.create(
            self.db,
            ConversationCreate(
                agent_name=agent_config.name,
                model=agent_config.model,
                agent_config={
                    "role_name": agent_config.role_name,
                    "persona": agent_config.persona,
                    "mission": agent_config.mission,
                },
            ),
        )
        return conv

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """Get a conversation by ID or raise.

        Filters soft-deleted records. This is a stopgap until
        pattern-stack's BaseService.get() handles soft-deletes
        consistently with list().
        """
        conv: Conversation | None = await self.conversation_service.get(self.db, conversation_id)
        if conv is None or conv.is_deleted:
            raise ConversationNotFoundError(conversation_id)
        return conv

    async def get_with_messages(self, conversation_id: UUID) -> dict[str, Any]:
        """Get conversation with all messages and parts."""
        conv = await self.get_conversation(conversation_id)
        messages = await self.message_service.get_by_conversation(self.db, conversation_id)

        message_data = []
        for msg in messages:
            parts = await self.message_part_service.get_by_message(self.db, msg.id)
            message_data.append({"message": msg, "parts": parts})

        tool_calls = await self.tool_call_service.get_by_conversation(self.db, conversation_id)

        return {
            "conversation": conv,
            "messages": message_data,
            "tool_calls": tool_calls,
        }

    async def add_message(
        self,
        conversation_id: UUID,
        kind: str,
        sequence: int,
        parts: list[dict[str, Any]],
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> Message:
        """Add a message with parts to a conversation."""
        conv = await self.get_conversation(conversation_id)

        # Ensure conversation is active
        if conv.state == "created":
            conv.transition_to("active")
            await self.db.flush()

        msg = await self.message_service.create(
            self.db,
            MessageCreate(
                conversation_id=conversation_id,
                kind=kind,
                sequence=sequence,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
        )

        for i, part_data in enumerate(parts):
            await self.message_part_service.create(
                self.db,
                MessagePartCreate(
                    message_id=msg.id,
                    position=i,
                    part_type=part_data.get("type", "text"),
                    content=part_data.get("content"),
                    tool_call_id=part_data.get("tool_call_id"),
                    tool_name=part_data.get("tool_name"),
                    tool_arguments=part_data.get("tool_arguments"),
                ),
            )

        # Update token counts
        if input_tokens or output_tokens:
            await self.conversation_service.update(
                self.db,
                conv.id,
                ConversationUpdate(
                    exchange_count=conv.exchange_count + (1 if kind == "response" else 0),
                    total_input_tokens=conv.total_input_tokens + (input_tokens or 0),
                    total_output_tokens=conv.total_output_tokens + (output_tokens or 0),
                ),
            )

        return msg

    async def list_filtered(
        self,
        *,
        agent_name: str | None = None,
        state: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Conversation], int]:
        """List conversations with optional filters."""
        filters: dict[str, Any] = {}
        if agent_name is not None:
            filters["agent_name"] = agent_name
        if state is not None:
            filters["state"] = state

        conversations, count = await self.conversation_service.list(
            self.db,
            offset=offset,
            limit=limit,
            filters=filters if filters else None,
            order_by=["-created_at"],
        )
        return list(conversations), count

    async def branch_conversation(
        self,
        conversation_id: UUID,
        at_sequence: int,
    ) -> Conversation:
        """Branch a conversation by copying messages up to at_sequence.

        Creates a new conversation linked to the original via branched_from_id,
        then copies all messages (with their parts) up to and including
        the given sequence number.
        """
        source = await self.get_conversation(conversation_id)
        data = await self.get_with_messages(conversation_id)

        # Create the branched conversation
        branch = await self.conversation_service.create(
            self.db,
            ConversationCreate(
                agent_name=source.agent_name,
                model=source.model,
                agent_config=source.agent_config,
                branched_from_id=source.id,
                branched_at_sequence=at_sequence,
            ),
        )

        # Copy messages up to at_sequence
        for msg_data in data["messages"]:
            msg = msg_data["message"]
            if msg.sequence > at_sequence:
                break

            parts = [
                {
                    "type": p.part_type,
                    "content": p.content,
                    "tool_call_id": p.tool_call_id,
                    "tool_name": p.tool_name,
                    "tool_arguments": p.tool_arguments,
                }
                for p in msg_data["parts"]
            ]

            await self.add_message(
                conversation_id=branch.id,
                kind=msg.kind,
                sequence=msg.sequence,
                parts=parts,
                input_tokens=msg.input_tokens,
                output_tokens=msg.output_tokens,
            )

        return branch  # type: ignore[no-any-return]

    async def delete_conversation(self, conversation_id: UUID) -> None:
        """Soft-delete a conversation."""
        conv = await self.get_conversation(conversation_id)
        conv.soft_delete()
        await self.db.flush()
