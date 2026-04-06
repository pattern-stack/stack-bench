from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pattern_stack.features.users.models import User
from pattern_stack.molecules.apis.auth import AuthAPI
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from molecules.apis.conversation_api import ConversationAPI
from molecules.apis.github_oauth_api import GitHubOAuthAPI
from molecules.apis.stack_api import StackAPI
from molecules.apis.task_api import TaskAPI
from molecules.providers.github_adapter import GitHubAdapter
from molecules.runtime.conversation_runner import ConversationRunner
from molecules.services.clone_manager import CloneManager
from molecules.services.gcp_client import GCPClient, GCPClientProtocol
from molecules.services.workspace_manager import WorkspaceManager

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_bearer_scheme = HTTPBearer(auto_error=False)
_auth_api = AuthAPI()
_github_oauth = GitHubOAuthAPI()


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Get database session from app state."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DatabaseSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
) -> User:
    """Resolve the currently authenticated user from the Bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await _auth_api.get_current_user(db, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    db: DatabaseSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
) -> User | None:
    """Optionally resolve the authenticated user; returns None if no token."""
    if not credentials:
        return None
    return await _auth_api.get_current_user(db, credentials.credentials)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


async def get_user_github_token(user: CurrentUser, db: DatabaseSession) -> str:
    """Resolve the user's GitHub access token from their Connection."""
    token = await _github_oauth.get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(403, detail="GitHub account not connected")
    return token


UserGitHubToken = Annotated[str, Depends(get_user_github_token)]


async def get_user_github_adapter(
    user: CurrentUser,
    db: DatabaseSession,
) -> GitHubAdapter:
    """Resolve GitHubAdapter using the authenticated user's OAuth token.

    Falls back to the settings GITHUB_TOKEN if the user has no connection
    (for read-only operations like diffs). Raises 403 for write ops that
    require a user token.
    """
    token = await _github_oauth.get_user_github_token(db, user.id)
    if token:
        return GitHubAdapter(token=token)
    # Fallback for read ops (diff, tree, file content)
    settings = get_settings()
    if settings.GITHUB_TOKEN:
        return GitHubAdapter(token=settings.GITHUB_TOKEN)
    raise HTTPException(403, detail="GitHub account not connected — connect via Settings")


UserGitHubAdapterDep = Annotated[GitHubAdapter, Depends(get_user_github_adapter)]


def get_stack_api_with_user(db: DatabaseSession, github: UserGitHubAdapterDep) -> StackAPI:
    return StackAPI(db, github)


UserStackAPIDep = Annotated[StackAPI, Depends(get_stack_api_with_user)]


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


def get_clone_manager() -> CloneManager:
    settings = get_settings()
    return CloneManager(
        base_dir=Path(settings.CLONE_BASE_DIR),
        max_clones=settings.CLONE_MAX_CONCURRENT,
        ttl_seconds=settings.CLONE_TTL_SECONDS,
        github_token=settings.GITHUB_TOKEN or None,
    )


CloneManagerDep = Annotated[CloneManager, Depends(get_clone_manager)]


def get_gcp_client() -> GCPClientProtocol:
    settings = get_settings()
    if not settings.GCP_PROJECT_ID or settings.GCP_PROJECT_ID == "local":
        from molecules.services.local_gcp_client import LocalGCPClient

        return LocalGCPClient(project_id=settings.GCP_PROJECT_ID or "local")
    return GCPClient(project_id=settings.GCP_PROJECT_ID)


GCPClientDep = Annotated[GCPClientProtocol, Depends(get_gcp_client)]


def get_workspace_manager(db: DatabaseSession, gcp_client: GCPClientDep) -> WorkspaceManager:
    return WorkspaceManager(db=db, gcp_client=gcp_client)


WorkspaceManagerDep = Annotated[WorkspaceManager, Depends(get_workspace_manager)]


def get_task_api(db: DatabaseSession) -> TaskAPI:
    return TaskAPI(db)


TaskAPIDep = Annotated[TaskAPI, Depends(get_task_api)]
