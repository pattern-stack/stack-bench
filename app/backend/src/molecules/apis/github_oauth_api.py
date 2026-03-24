from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet

from config.settings import get_settings
from features.github_connections.schemas.input import GitHubConnectionCreate
from features.github_connections.schemas.output import GitHubConnectionResponse
from features.github_connections.service import GitHubConnectionService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Module-level state store (single-process MVP)
# state -> (code_verifier, expires_at_timestamp)
_pending_oauth: dict[str, tuple[str, float]] = {}

# TTL for pending OAuth state (10 minutes)
_STATE_TTL_SECONDS = 600

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def cleanup_expired_state() -> None:
    """Remove expired entries from the pending OAuth state store."""
    now = time.time()
    expired_keys = [k for k, (_, expires_at) in _pending_oauth.items() if expires_at < now]
    for key in expired_keys:
        del _pending_oauth[key]


def _compute_s256_challenge(code_verifier: str) -> str:
    """Compute S256 PKCE code challenge from code verifier (RFC 7636)."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class GitHubOAuthAPI:
    """GitHub OAuth business logic.

    Responsibilities:
    - Generate authorization URL with PKCE challenge
    - Exchange authorization code for tokens
    - Encrypt and store tokens
    - Retrieve connection status
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.service = GitHubConnectionService()
        self.settings = get_settings()

    def build_authorize_url(self, code_verifier: str) -> tuple[str, str]:
        """Build GitHub authorization URL with PKCE.

        Returns (authorize_url, state) where state is a random
        CSRF token that must be verified on callback.
        """
        # Clean up any expired state entries
        cleanup_expired_state()

        # Generate random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Compute S256 challenge from verifier
        code_challenge = _compute_s256_challenge(code_verifier)

        # Store verifier keyed by state for callback retrieval
        _pending_oauth[state] = (code_verifier, time.time() + _STATE_TTL_SECONDS)

        # Build the authorization URL
        params = {
            "client_id": self.settings.GITHUB_APP_CLIENT_ID,
            "redirect_uri": self.settings.GITHUB_OAUTH_REDIRECT_URI,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
        return url, state

    async def handle_callback(self, code: str, state: str) -> GitHubConnectionResponse:
        """Exchange code for tokens, fetch user profile, store connection.

        Steps:
        1. Validate and retrieve code_verifier from state store
        2. POST to GitHub token endpoint with code + code_verifier
        3. GET /user to fetch github_user_id and github_login
        4. Encrypt tokens
        5. Upsert into github_connections
        """
        # Validate state
        if state not in _pending_oauth:
            raise ValueError(f"Invalid or unknown OAuth state: {state}")

        code_verifier, expires_at = _pending_oauth.pop(state)

        if time.time() > expires_at:
            raise ValueError(f"OAuth state expired for state: {state}")

        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GITHUB_TOKEN_URL,
                json={
                    "client_id": self.settings.GITHUB_APP_CLIENT_ID,
                    "client_secret": self.settings.GITHUB_APP_CLIENT_SECRET,
                    "code": code,
                    "code_verifier": code_verifier,
                    "redirect_uri": self.settings.GITHUB_OAUTH_REDIRECT_URI,
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            # Fetch GitHub user profile
            user_response = await client.get(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {token_data['access_token']}",
                    "Accept": "application/json",
                },
            )
            user_response.raise_for_status()
            user_data = user_response.json()

        # Compute expiry timestamps
        now = datetime.now(tz=timezone.utc)
        token_expires_at = None
        refresh_token_expires_at = None
        if "expires_in" in token_data:
            from datetime import timedelta

            token_expires_at = now + timedelta(seconds=token_data["expires_in"])
        if "refresh_token_expires_in" in token_data:
            from datetime import timedelta

            refresh_token_expires_at = now + timedelta(seconds=token_data["refresh_token_expires_in"])

        # Encrypt tokens as a single JSON blob
        token_blob = json.dumps({
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "expires_in": token_data.get("expires_in"),
            "refresh_token_expires_in": token_data.get("refresh_token_expires_in"),
        }).encode("utf-8")

        fernet = Fernet(self.settings.ENCRYPTION_KEY.encode())
        tokens_encrypted = fernet.encrypt(token_blob)

        # Upsert connection
        create_data = GitHubConnectionCreate(
            github_user_id=user_data["id"],
            github_login=user_data["login"],
            tokens_encrypted=tokens_encrypted,
            token_expires_at=token_expires_at,
            refresh_token_expires_at=refresh_token_expires_at,
        )
        connection = await self.service.upsert(self.db, create_data)

        return GitHubConnectionResponse.model_validate(connection)

    async def get_connection_status(self) -> GitHubConnectionResponse | None:
        """Get current GitHub connection (if any).

        Single-tenant MVP: returns the first (and only) connection.
        Multi-user: will filter by user_id.
        """
        connections, total = await self.service.list(self.db, offset=0, limit=1)
        if not connections:
            return None
        return GitHubConnectionResponse.model_validate(connections[0])
