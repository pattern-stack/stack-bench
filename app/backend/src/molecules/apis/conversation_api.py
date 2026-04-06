from __future__ import annotations

from datetime import datetime  # noqa: TCH003
from typing import TYPE_CHECKING, Any
from uuid import UUID  # noqa: TCH003

from pydantic import BaseModel

from features.conversations.schemas.output import ConversationResponse
from features.conversations.service import ConversationService
from molecules.agents.assembler import AgentAssembler
from molecules.entities.conversation_entity import ConversationEntity

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ConversationDetailResponse(BaseModel):
    """Full conversation with messages."""

    id: UUID
    agent_name: str
    model: str
    state: str
    conversation_type: str = "execution"
    exchange_count: int
    total_input_tokens: int
    total_output_tokens: int
    branched_from_id: UUID | None = None
    branched_at_sequence: int | None = None
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class AgentDetailResponse(BaseModel):
    """Agent configuration details."""

    name: str
    role_name: str
    model: str
    mission: str
    background: str | None = None
    model_config = {"from_attributes": True}


class ConversationAPI:
    """API facade for conversation domain.

    Both REST and CLI consume this. Permissions will be added here when auth is implemented.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.entity = ConversationEntity(db)
        self.assembler = AgentAssembler(db)
        self.link_service = ConversationService()

    async def create(self, agent_name: str, model: str | None = None) -> ConversationResponse:
        """Create a new conversation."""
        conv = await self.entity.create_conversation(agent_name, model)
        await self.db.commit()
        return ConversationResponse.model_validate(conv)

    async def get(self, conversation_id: UUID) -> ConversationDetailResponse:
        """Get a conversation with messages and tool calls."""
        data = await self.entity.get_with_messages(conversation_id)
        conv = data["conversation"]
        messages = [
            {
                "id": str(m["message"].id),
                "kind": m["message"].kind,
                "sequence": m["message"].sequence,
                "parts": [
                    {
                        "type": p.part_type,
                        "content": p.content,
                    }
                    for p in m["parts"]
                ],
            }
            for m in data["messages"]
        ]
        tool_calls_data = [
            {
                "id": str(tc.id),
                "tool_name": tc.tool_name,
                "state": tc.state,
            }
            for tc in data["tool_calls"]
        ]
        return ConversationDetailResponse(
            id=conv.id,
            agent_name=conv.agent_name,
            model=conv.model,
            state=conv.state,
            conversation_type=getattr(conv, "conversation_type", "execution"),
            exchange_count=conv.exchange_count,
            total_input_tokens=conv.total_input_tokens,
            total_output_tokens=conv.total_output_tokens,
            branched_from_id=conv.branched_from_id,
            branched_at_sequence=conv.branched_at_sequence,
            messages=messages,
            tool_calls=tool_calls_data,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    async def list(
        self,
        *,
        agent_name: str | None = None,
        state: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConversationResponse]:
        """List conversations with optional filters."""
        convs, _count = await self.entity.list_filtered(
            agent_name=agent_name,
            state=state,
            limit=limit,
            offset=offset,
        )
        return [ConversationResponse.model_validate(c) for c in convs]

    async def delete(self, conversation_id: UUID) -> None:
        """Soft-delete a conversation."""
        await self.entity.delete_conversation(conversation_id)
        await self.db.commit()

    async def branch(
        self,
        conversation_id: UUID,
        at_sequence: int,
    ) -> ConversationResponse:
        """Branch a conversation at a given message sequence."""
        conv = await self.entity.branch_conversation(conversation_id, at_sequence)
        await self.db.commit()
        return ConversationResponse.model_validate(conv)

    async def get_by_entity(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        role: str,
    ) -> ConversationResponse | None:
        """Get the active conversation linked to an entity with a specific role."""
        link = await self.link_service.get_conversation_for_entity(
            self.db,
            entity_type=entity_type,
            entity_id=entity_id,
            role=role,
        )
        if link is None:
            return None
        conv = await self.entity.get_conversation(link.entity_a_id)
        return ConversationResponse.model_validate(conv)

    async def list_agents(self) -> list[str]:  # type: ignore[valid-type]
        """List available agent names."""
        return await self.assembler.list_available()

    async def get_agent(self, name: str) -> AgentDetailResponse:
        """Get agent configuration details."""
        config = await self.assembler.assemble(name)
        return AgentDetailResponse(
            name=config.name,
            role_name=config.role_name,
            model=config.model,
            mission=config.mission,
            background=config.background,
        )
