from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from molecules.apis.conversation_api import ConversationAPI
from molecules.apis.stack_api import StackAPI
from molecules.providers.github_adapter import GitHubAdapter
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


def get_github_adapter() -> GitHubAdapter:
    settings = get_settings()
    return GitHubAdapter(token=settings.GITHUB_TOKEN)


GitHubAdapterDep = Annotated[GitHubAdapter, Depends(get_github_adapter)]


def get_stack_api(db: DatabaseSession, github: GitHubAdapterDep) -> StackAPI:
    return StackAPI(db, github)


StackAPIDep = Annotated[StackAPI, Depends(get_stack_api)]
