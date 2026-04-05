from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService

from .models import ConversationLink

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ConversationLinkCreate:
    """Thin creation helper — BaseService.create takes a schema or dict."""

    pass


class ConversationLinkUpdate:
    """Placeholder for BaseService typing."""

    pass


class ConversationLinkService(BaseService[ConversationLink, ConversationLinkCreate, ConversationLinkUpdate]):
    model = ConversationLink

    async def link_conversation(
        self,
        db: AsyncSession,
        *,
        conversation_id: UUID,
        entity_type: str,
        entity_id: UUID,
        relationship_type: str,
    ) -> ConversationLink:
        """Create a link between a conversation and an entity."""
        link = ConversationLink(
            entity_a_type="conversation",
            entity_a_id=conversation_id,
            entity_b_type=entity_type,
            entity_b_id=entity_id,
            relationship_type=relationship_type,
            is_active=True,
        )
        db.add(link)
        return link

    async def get_conversation_for_entity(
        self,
        db: AsyncSession,
        *,
        entity_type: str,
        entity_id: UUID,
        role: str,
    ) -> ConversationLink | None:
        """Find the active link for a specific entity and role."""
        links = await ConversationLink.get_active_relations(db, entity_id, entity_type)
        for link in links:
            if link.relationship_type == role and link.entity_a_type == "conversation":
                return link
        return None

    async def get_links_for_conversation(
        self,
        db: AsyncSession,
        *,
        conversation_id: UUID,
    ) -> list[ConversationLink]:
        """Get all active links for a conversation."""
        return await ConversationLink.get_active_relations(db, conversation_id, "conversation")
