from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ToolCall
from .schemas.input import ToolCallCreate, ToolCallUpdate


class ToolCallService(BaseService[ToolCall, ToolCallCreate, ToolCallUpdate]):
    model = ToolCall

    async def get_by_conversation(self, db: AsyncSession, conversation_id: UUID) -> list[ToolCall]:
        """Get tool calls for a conversation ordered by creation time."""
        result = await db.execute(
            select(ToolCall).where(ToolCall.conversation_id == conversation_id).order_by(ToolCall.created_at)
        )
        return list(result.scalars().all())
