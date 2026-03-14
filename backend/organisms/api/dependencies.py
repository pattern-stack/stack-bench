from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from molecules.apis.conversation_api import ConversationAPI


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session. Will be wired to real engine in SB-007."""
    # Placeholder — SB-007 wires the real session factory
    raise NotImplementedError("Database session not configured. See SB-007.")
    yield


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def get_conversation_api(db: DatabaseSession) -> ConversationAPI:
    return ConversationAPI(db)


ConversationAPIDep = Annotated[ConversationAPI, Depends(get_conversation_api)]
