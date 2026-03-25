"""GitHub OAuth API molecule — business logic for GitHub App OAuth flow.

No HTTP concerns. Handles token exchange, user linking, and encrypted
Connection storage. Used by the auth router (organisms layer).
"""

import time
import urllib.parse
from typing import Any
from uuid import UUID

import httpx
from pattern_stack.atoms.integrations.encryption import decrypt_config, encrypt_config
from pattern_stack.atoms.integrations.models import Connection
from pattern_stack.features.users.models import User
from pattern_stack.features.users.service import UserService
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings

# GitHub OAuth URLs
AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
USER_EMAILS_URL = "https://api.github.com/user/emails"

# Scopes requested for the GitHub OAuth flow
OAUTH_SCOPE = "repo read:org read:user user:email"

# Refresh buffer: refresh tokens 5 minutes before they expire
REFRESH_BUFFER_SECONDS = 300


class GitHubOAuthAPI:
    """Business logic molecule for GitHub App OAuth integration.

    Responsibilities:
    - Generate GitHub OAuth authorization URLs
    - Exchange authorization codes for tokens
    - Fetch GitHub user profiles
    - Create/link Stack Bench users from GitHub accounts
    - Store/retrieve encrypted GitHub tokens in Connection model
    - Auto-refresh expired tokens
    """

    def __init__(self, user_service: UserService | None = None) -> None:
        self.user_service = user_service or UserService()

    def get_authorize_url(self, state: str) -> str:
        """Generate GitHub OAuth authorization URL."""
        settings = get_settings()
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": f"{settings.FRONTEND_URL}/auth/github/callback",
            "scope": OAUTH_SCOPE,
            "state": state,
        }
        return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any] | None:
        """POST to GitHub to exchange auth code for access + refresh tokens."""
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TOKEN_URL,
                json={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
        if response.status_code != 200:
            return None
        data = response.json()
        if "error" in data:
            return None
        return dict(data)

    async def get_github_user(self, access_token: str) -> dict[str, Any]:
        """GET /user from GitHub API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            return dict(response.json())

    async def get_github_emails(self, access_token: str) -> list[dict[str, Any]]:
        """GET /user/emails from GitHub API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                USER_EMAILS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            return list(response.json())

    async def find_or_create_user_from_github(
        self,
        db: AsyncSession,
        github_user: dict[str, Any],
        github_emails: list[dict[str, Any]],
    ) -> tuple[User, bool]:
        """Find existing user by GitHub ID or email, or create a new one.

        Returns (user, is_new).
        """
        github_id = str(github_user["id"])
        github_login = github_user.get("login", "")

        # 1. Search by GitHub ID in oauth_accounts using JSONB path query
        jsonb_accounts = cast(User.oauth_accounts, JSONB)
        result = await db.execute(
            select(User).where(
                User.is_active.is_(True),
                jsonb_accounts["github"]["id"].astext == github_id,
            )
        )
        existing_by_gh = result.scalars().first()
        if existing_by_gh:
            accts: dict[str, Any] = existing_by_gh.oauth_accounts or {}  # type: ignore[assignment]
            accts["github"]["login"] = github_login
            existing_by_gh.oauth_accounts = accts
            return existing_by_gh, False

        # 2. Find primary verified email from GitHub
        primary_email = None
        for email_info in github_emails:
            if email_info.get("primary") and email_info.get("verified"):
                primary_email = email_info["email"]
                break
        if not primary_email:
            # Fall back to any verified email
            for email_info in github_emails:
                if email_info.get("verified"):
                    primary_email = email_info["email"]
                    break
        if not primary_email:
            primary_email = github_user.get("email") or f"{github_login}@github.noreply.com"

        # 3. Search by email
        existing = await self.user_service.get_by_email(db, primary_email)
        if existing:
            # Link GitHub to existing account
            existing_accts: dict[str, Any] = existing.oauth_accounts or {}  # type: ignore[assignment]
            existing_accts["github"] = {"id": github_id, "login": github_login}
            existing.oauth_accounts = existing_accts
            return existing, False

        # 4. Create new OAuth-only user
        name_parts = (github_user.get("name") or github_login).split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        new_user = User(
            first_name=first_name,
            last_name=last_name or first_name,  # last_name required
            email=primary_email,
            oauth_accounts={"github": {"id": github_id, "login": github_login}},
            is_active=True,
        )
        db.add(new_user)
        await db.flush()
        return new_user, True

    async def store_github_connection(
        self,
        db: AsyncSession,
        user_id: UUID,
        token_data: dict[str, Any],
        github_user: dict[str, Any],
    ) -> Connection:
        """Create or update a Connection with encrypted GitHub token config."""
        settings = get_settings()
        encryption_key = settings.ENCRYPTION_KEY.encode() if settings.ENCRYPTION_KEY else None

        config_payload = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "bearer"),
            "expires_at": token_data.get("expires_in", 0) + int(time.time()) if token_data.get("expires_in") else None,
            "refresh_token_expires_at": token_data.get("refresh_token_expires_in", 0) + int(time.time())
            if token_data.get("refresh_token_expires_in")
            else None,
            "github_user_id": github_user.get("id"),
            "github_login": github_user.get("login"),
            "scope": token_data.get("scope", ""),
        }

        # Encrypt config if we have a key, otherwise store as empty bytes
        if encryption_key:
            encrypted = encrypt_config(config_payload, encryption_key)
        else:
            import json

            encrypted = json.dumps(config_payload).encode()

        # Check for existing connection
        existing = await self.get_user_connection(db, user_id)
        if existing:
            existing.config_encrypted = encrypted
            existing.status = "active"
            existing.last_error = None  # type: ignore[assignment]
            return existing

        # Create new connection
        connection = Connection(
            provider="github",
            name=f"GitHub ({github_user.get('login', 'unknown')})",
            webhook_path=f"github-{user_id.hex[:12]}",
            config_encrypted=encrypted,
            enabled=True,
            team_id=user_id,
            status="active",
        )
        db.add(connection)
        await db.flush()
        return connection

    async def get_user_connection(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> Connection | None:
        """Query active Connection where provider='github' and team_id=user_id."""
        result = await db.execute(
            select(Connection).where(
                Connection.provider == "github",
                Connection.team_id == user_id,
                Connection.enabled.is_(True),
            )
        )
        return result.scalars().first()

    async def get_connection_status(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Return connection status for a user's GitHub account.

        Returns {"connected": bool, "github_login": str | None}.
        """
        connection = await self.get_user_connection(db, user_id)
        if connection:
            settings = get_settings()
            if settings.ENCRYPTION_KEY:
                config = decrypt_config(
                    connection.config_encrypted,
                    settings.ENCRYPTION_KEY.encode(),
                )
                return {"connected": True, "github_login": config.get("github_login")}
        return {"connected": False, "github_login": None}

    async def disconnect(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> None:
        """Soft-delete a user's GitHub connection by disabling it."""
        connection = await self.get_user_connection(db, user_id)
        if connection:
            connection.enabled = False
            await db.flush()

    async def get_user_github_token(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> str | None:
        """Decrypt Connection config, check expiry, auto-refresh if needed."""
        connection = await self.get_user_connection(db, user_id)
        if not connection:
            return None

        settings = get_settings()
        encryption_key = settings.ENCRYPTION_KEY.encode() if settings.ENCRYPTION_KEY else None

        if encryption_key:
            config = decrypt_config(connection.config_encrypted, encryption_key)
        else:
            import json

            config = json.loads(connection.config_encrypted.decode())

        access_token = config.get("access_token")
        expires_at = config.get("expires_at")

        # Check if token needs refresh
        if expires_at and time.time() > (expires_at - REFRESH_BUFFER_SECONDS):
            refresh_token = config.get("refresh_token")
            if refresh_token:
                new_data = await self._refresh_github_token(refresh_token)
                if new_data:
                    config["access_token"] = new_data["access_token"]
                    if new_data.get("refresh_token"):
                        config["refresh_token"] = new_data["refresh_token"]
                    if new_data.get("expires_in"):
                        config["expires_at"] = int(time.time()) + new_data["expires_in"]

                    # Update stored connection
                    if encryption_key:
                        connection.config_encrypted = encrypt_config(config, encryption_key)
                    else:
                        import json

                        connection.config_encrypted = json.dumps(config).encode()
                    await db.flush()
                    return str(config["access_token"])

            # Refresh failed and token expired
            if time.time() > expires_at:
                return None

        return str(access_token) if access_token else None

    async def _refresh_github_token(self, refresh_token: str) -> dict[str, Any] | None:
        """POST refresh_token grant to GitHub token endpoint."""
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TOKEN_URL,
                json={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                headers={"Accept": "application/json"},
            )
        if response.status_code != 200:
            return None
        data = response.json()
        if "error" in data:
            return None
        return dict(data)
