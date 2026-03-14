from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Message
from .schemas.input import MessageCreate, MessageUpdate


class MessageService(BaseService[Message, MessageCreate, MessageUpdate]):  # type: ignore[misc]
    model = Message

    async def get_by_conversation(self, db: AsyncSession, conversation_id: UUID, *, limit: int = 100) -> list[Message]:
        """Get messages for a conversation ordered by sequence."""
        result = await db.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.sequence).limit(limit)
        )
        return list(result.scalars().all())
