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
    redirect_origin: str | None = None


class GitHubConnectionStatus(BaseModel):
    connected: bool
    github_login: str | None = None
    needs_reauth: bool = False


@router.get("/github", response_model=GitHubAuthorizeResponse)
async def github_login(redirect_origin: str | None = None) -> GitHubAuthorizeResponse:
    """Return GitHub OAuth authorization URL.

    If redirect_origin is provided (e.g. http://localhost:3502), it overrides
    the FRONTEND_URL setting for building the redirect_uri. This supports
    dynamic dev ports where the frontend may not be on a fixed port.
    """
    state = secrets.token_urlsafe(32)
    url = github_oauth.get_authorize_url(state, redirect_origin=redirect_origin)
    return GitHubAuthorizeResponse(authorize_url=url, state=state)


class GitHubCallbackResponse(BaseModel):
    connected: bool
    github_login: str | None = None


@router.post("/github/callback", response_model=GitHubCallbackResponse)
async def github_callback(
    data: GitHubCallbackRequest,
    user: CurrentUser,
    db: DatabaseSession,
) -> GitHubCallbackResponse:
    """Exchange GitHub auth code for tokens and store as Connection for the authenticated user.

    Users are created only through pattern-stack auth (register/login).
    GitHub is an integration — stored as a Connection linked to the user.
    """
    # 1. Exchange code for GitHub tokens (redirect_uri must match the one used in authorize)
    token_data = await github_oauth.exchange_code(data.code, redirect_origin=data.redirect_origin)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid GitHub authorization code")

    # 2. Fetch GitHub user profile
    github_user = await github_oauth.get_github_user(token_data["access_token"])

    # 3. Store GitHub tokens as Connection for the authenticated user
    await github_oauth.store_github_connection(db, user.id, token_data, github_user)

    await db.commit()

    return GitHubCallbackResponse(
        connected=True,
        github_login=github_user.get("login"),
    )


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
