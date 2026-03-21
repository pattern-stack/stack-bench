from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from molecules.apis.conversation_api import ConversationAPI
from molecules.apis.stack_api import StackAPI
from molecules.runtime.conversation_runner import ConversationRunner


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Get database session from app state."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def get_conversation_api(db: DatabaseSession) -> ConversationAPI:
    return ConversationAPI(db)


ConversationAPIDep = Annotated[ConversationAPI, Depends(get_conversation_api)]


def get_conversation_runner(db: DatabaseSession) -> ConversationRunner:
    return ConversationRunner(db)


ConversationRunnerDep = Annotated[ConversationRunner, Depends(get_conversation_runner)]


def get_stack_api(db: DatabaseSession) -> StackAPI:
    return StackAPI(db)


StackAPIDep = Annotated[StackAPI, Depends(get_stack_api)]
