from __future__ import annotations

from typing import TYPE_CHECKING

from pattern_stack.atoms.patterns.services import BaseService

from .models import Conversation, ConversationContext
from .schemas.input import ConversationCreate, ConversationUpdate

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class ConversationService(BaseService[Conversation, ConversationCreate, ConversationUpdate]):
    model = Conversation

    async def link_conversation(
        self,
        db: AsyncSession,
        *,
        conversation_id: UUID,
        entity_type: str,
        entity_id: UUID,
        relationship_type: str,
    ) -> ConversationContext:
        """Create a context link between a conversation and an entity."""
        ctx = ConversationContext(
            conversation_id=conversation_id,
            target_type=entity_type,
            target_id=entity_id,
            role=relationship_type,
            is_active=True,
        )
        db.add(ctx)
        return ctx

    async def get_conversation_for_entity(
        self,
        db: AsyncSession,
        *,
        entity_type: str,
        entity_id: UUID,
        role: str,
    ) -> ConversationContext | None:
        """Find the active context link for a specific entity and role."""
        links: list[ConversationContext] = await ConversationContext.get_active_relations(db, entity_id, entity_type)  # type: ignore[assignment]
        for link in links:
            if link.relationship_type == role and link.entity_a_type == "conversation":
                return link
        return None

    async def get_links_for_conversation(
        self,
        db: AsyncSession,
        *,
        conversation_id: UUID,
    ) -> list[ConversationContext]:
        """Get all active context links for a conversation."""
        return await ConversationContext.get_active_relations(db, conversation_id, "conversation")  # type: ignore[return-value]
