from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import MessagePart
from .schemas.input import MessagePartCreate, MessagePartUpdate


class MessagePartService(BaseService[MessagePart, MessagePartCreate, MessagePartUpdate]):
    model = MessagePart

    async def get_by_message(self, db: AsyncSession, message_id: UUID) -> list[MessagePart]:
        """Get parts for a message ordered by position."""
        result = await db.execute(
            select(MessagePart).where(MessagePart.message_id == message_id).order_by(MessagePart.position)
        )
        return list(result.scalars().all())
