"""Auth router — thin interface layer delegating to pattern-stack's AuthAPI.

Provides login, register, refresh, me endpoints (Phase 1) and
GitHub OAuth flow endpoints (Phase 2).
"""

import secrets

from fastapi import APIRouter, HTTPException
from pattern_stack.features.auth.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidRefreshTokenError,
    WeakPasswordError,
)
from pattern_stack.features.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from pattern_stack.features.auth.schemas.output import RefreshResult, TokenResponse
from pattern_stack.features.users.schemas.output import UserResponse
from pattern_stack.molecules.apis.auth import AuthAPI
from pydantic import BaseModel

from molecules.apis.github_oauth_api import GitHubOAuthAPI
from organisms.api.dependencies import CurrentUser, DatabaseSession

router = APIRouter(prefix="/auth", tags=["auth"])
auth_api = AuthAPI()
github_oauth = GitHubOAuthAPI()


# ---------------------------------------------------------------------------
# Phase 1: User authentication
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DatabaseSession) -> TokenResponse:
    """Authenticate user with email and password."""
    result = await auth_api.login(db, data)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    await db.commit()
    return result.to_token_response()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, db: DatabaseSession) -> TokenResponse:
    """Register a new user account."""
    try:
        result = await auth_api.register(db, data)
        await db.commit()
        return result.to_token_response()
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    except WeakPasswordError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/refresh", response_model=RefreshResult)
async def refresh(data: RefreshRequest, db: DatabaseSession) -> RefreshResult:
    """Refresh an access token using a refresh token."""
    try:
        return await auth_api.refresh_tokens(db, data.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    """Get the currently authenticated user."""
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# Phase 2: GitHub OAuth
# ---------------------------------------------------------------------------


class GitHubAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


class GitHubCallbackRequest(BaseModel):
    code: str
    state: str


class GitHubConnectionStatus(BaseModel):
    connected: bool
    github_login: str | None = None


@router.get("/github", response_model=GitHubAuthorizeResponse)
async def github_login() -> GitHubAuthorizeResponse:
    """Return GitHub OAuth authorization URL."""
    state = secrets.token_urlsafe(32)
    url = github_oauth.get_authorize_url(state)
    return GitHubAuthorizeResponse(authorize_url=url, state=state)


@router.post("/github/callback", response_model=TokenResponse)
async def github_callback(
    data: GitHubCallbackRequest,
    db: DatabaseSession,
) -> TokenResponse:
    """Exchange GitHub auth code for tokens, create/link user, return JWT."""
    # 1. Exchange code for GitHub tokens
    token_data = await github_oauth.exchange_code(data.code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid GitHub authorization code")

    # 2. Fetch GitHub user profile + emails
    github_user = await github_oauth.get_github_user(token_data["access_token"])
    github_emails = await github_oauth.get_github_emails(token_data["access_token"])

    # 3. Find or create user
    user, _is_new = await github_oauth.find_or_create_user_from_github(db, github_user, github_emails)

    # 4. Store GitHub tokens as encrypted Connection
    await github_oauth.store_github_connection(db, user.id, token_data, github_user)

    await db.commit()

    # 5. Generate Stack Bench JWT tokens
    result = auth_api._create_auth_result(user)
    return result.to_token_response()


@router.get("/github/status", response_model=GitHubConnectionStatus)
async def github_connection_status(
    user: CurrentUser,
    db: DatabaseSession,
) -> GitHubConnectionStatus:
    """Check if current user has connected GitHub account."""
    status = await github_oauth.get_connection_status(db, user.id)
    return GitHubConnectionStatus(**status)


@router.delete("/github", status_code=204)
async def disconnect_github(
    user: CurrentUser,
    db: DatabaseSession,
) -> None:
    """Disconnect GitHub account (soft-delete Connection)."""
    await github_oauth.disconnect(db, user.id)
    await db.commit()
