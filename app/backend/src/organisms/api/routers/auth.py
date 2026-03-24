from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from config.settings import get_settings
from molecules.apis.github_oauth_api import GitHubOAuthAPI

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/auth", tags=["auth"])

# Dependency override hook for testing
_get_db_override = None


async def _get_db(request: Request) -> AsyncSession:  # type: ignore[misc]
    """Get database session -- uses override if set (for testing)."""
    if _get_db_override is not None:
        async for session in _get_db_override():
            yield session  # type: ignore[misc]
        return
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


@router.get("/github")
async def github_auth_redirect(
    code_verifier: str,
    db: AsyncSession = Depends(_get_db),  # noqa: B008
) -> RedirectResponse:
    """Redirect to GitHub authorization page.

    Frontend generates PKCE code_verifier, passes it here.
    Backend computes challenge and redirects to GitHub.
    """
    api = GitHubOAuthAPI(db)
    url, _state = api.build_authorize_url(code_verifier)
    return RedirectResponse(url=url)


@router.get("/github/callback")
async def github_auth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(_get_db),  # noqa: B008
) -> RedirectResponse:
    """Handle GitHub OAuth callback.

    Exchanges code for tokens, stores connection, redirects to frontend.
    On success: redirect to FRONTEND_URL/?github=connected
    On error: redirect to FRONTEND_URL/?github=error&message=...
    """
    settings = get_settings()
    frontend_url = settings.FRONTEND_URL

    try:
        api = GitHubOAuthAPI(db)
        await api.handle_callback(code, state)
        await db.commit()
        redirect_url = f"{frontend_url}/?github=connected"
    except (ValueError, Exception) as exc:
        params = urlencode({"github": "error", "message": str(exc)})
        redirect_url = f"{frontend_url}/?{params}"

    return RedirectResponse(url=redirect_url)


@router.get("/github/status")
async def github_connection_status(
    db: AsyncSession = Depends(_get_db),  # noqa: B008
) -> dict[str, object]:
    """Check if GitHub is connected.

    Returns { connected: bool, github_login: str | null, ... }
    """
    api = GitHubOAuthAPI(db)
    connection = await api.get_connection_status()

    if connection is None:
        return {"connected": False, "github_login": None}

    return {
        "connected": connection.connected,
        "github_login": connection.github_login,
        "github_user_id": connection.github_user_id,
        "token_expires_at": connection.token_expires_at.isoformat() if connection.token_expires_at else None,
    }
