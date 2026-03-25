"""Unit tests for GitHubOAuthAPI molecule (Phase 2)."""

import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pattern_stack.atoms.integrations.encryption import encrypt_config, generate_key
from pattern_stack.atoms.integrations.models import Connection
from pattern_stack.features.users.models import User

from molecules.apis.github_oauth_api import (
    AUTHORIZE_URL,
    GitHubOAuthAPI,
)


@pytest.fixture
def oauth_api():
    return GitHubOAuthAPI()


@pytest.fixture
def encryption_key():
    return generate_key()


# --- URL generation ---


@pytest.mark.unit
class TestGetAuthorizeUrl:
    def test_returns_correct_url_with_params(self, oauth_api):
        url = oauth_api.get_authorize_url("test-state-123")
        assert url.startswith(AUTHORIZE_URL)
        assert "client_id=" in url
        assert "state=test-state-123" in url
        assert "scope=" in url

    def test_includes_redirect_uri(self, oauth_api):
        url = oauth_api.get_authorize_url("s")
        assert "redirect_uri=" in url
        assert "%2Fauth%2Fgithub%2Fcallback" in url


# --- Code exchange ---


@pytest.mark.unit
class TestExchangeCode:
    async def test_exchange_code_success(self, oauth_api):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "ghu_test123",
            "refresh_token": "ghr_test456",
            "token_type": "bearer",
            "scope": "repo",
        }

        with patch("molecules.apis.github_oauth_api.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await oauth_api.exchange_code("test-code")

        assert result is not None
        assert result["access_token"] == "ghu_test123"

    async def test_exchange_code_error_response(self, oauth_api):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "bad_verification_code"}

        with patch("molecules.apis.github_oauth_api.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await oauth_api.exchange_code("bad-code")

        assert result is None


# --- Connection storage ---


@pytest.mark.integration
class TestStoreGitHubConnection:
    async def test_creates_new_connection(self, db, oauth_api, encryption_key):
        user = User(
            first_name="Test",
            last_name="User",
            email="conn@test.com",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        token_data = {
            "access_token": "ghu_abc",
            "refresh_token": "ghr_def",
            "token_type": "bearer",
            "expires_in": 28800,
        }
        github_user = {"id": 12345, "login": "testuser"}

        with patch("molecules.apis.github_oauth_api.get_settings") as mock_settings:
            mock_settings.return_value.ENCRYPTION_KEY = encryption_key.decode()
            mock_settings.return_value.GITHUB_CLIENT_ID = "test"
            mock_settings.return_value.GITHUB_CLIENT_SECRET = "test"
            conn = await oauth_api.store_github_connection(db, user.id, token_data, github_user)

        assert conn.provider == "github"
        assert conn.team_id == user.id
        assert conn.status == "active"
        assert conn.config_encrypted is not None

    async def test_updates_existing_connection(self, db, oauth_api, encryption_key):
        user = User(
            first_name="Test",
            last_name="User2",
            email="conn2@test.com",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create initial connection
        initial_config = encrypt_config({"access_token": "old"}, encryption_key)
        existing = Connection(
            provider="github",
            name="GitHub (old)",
            webhook_path=f"github-{user.id.hex[:12]}",
            config_encrypted=initial_config,
            team_id=user.id,
            status="active",
        )
        db.add(existing)
        await db.flush()
        existing_id = existing.id

        token_data = {
            "access_token": "ghu_new",
            "refresh_token": "ghr_new",
            "token_type": "bearer",
        }
        github_user = {"id": 99999, "login": "newuser"}

        with patch("molecules.apis.github_oauth_api.get_settings") as mock_settings:
            mock_settings.return_value.ENCRYPTION_KEY = encryption_key.decode()
            mock_settings.return_value.GITHUB_CLIENT_ID = "test"
            mock_settings.return_value.GITHUB_CLIENT_SECRET = "test"
            conn = await oauth_api.store_github_connection(db, user.id, token_data, github_user)

        # Should update, not create a new one
        assert conn.id == existing_id


# --- Token retrieval ---


@pytest.mark.integration
class TestGetUserGitHubToken:
    async def test_valid_token_returned(self, db, oauth_api, encryption_key):
        user = User(
            first_name="Token",
            last_name="User",
            email="token@test.com",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        config = {
            "access_token": "ghu_valid",
            "refresh_token": "ghr_valid",
            "expires_at": int(time.time()) + 3600,  # 1 hour from now
        }
        conn = Connection(
            provider="github",
            name="GitHub (token)",
            webhook_path=f"github-tok-{user.id.hex[:12]}",
            config_encrypted=encrypt_config(config, encryption_key),
            team_id=user.id,
            status="active",
        )
        db.add(conn)
        await db.flush()

        with patch("molecules.apis.github_oauth_api.get_settings") as mock_settings:
            mock_settings.return_value.ENCRYPTION_KEY = encryption_key.decode()
            token = await oauth_api.get_user_github_token(db, user.id)

        assert token == "ghu_valid"

    async def test_no_connection_returns_none(self, db, oauth_api):
        user_id = uuid4()
        with patch("molecules.apis.github_oauth_api.get_settings") as mock_settings:
            mock_settings.return_value.ENCRYPTION_KEY = "test-key"
            token = await oauth_api.get_user_github_token(db, user_id)

        assert token is None


# --- User linking ---


@pytest.mark.integration
class TestFindOrCreateUser:
    async def test_creates_new_user(self, db, oauth_api):
        github_user = {"id": 11111, "login": "newghuser", "name": "New GitHub User"}
        emails = [{"email": "new@github.com", "primary": True, "verified": True}]

        user, is_new = await oauth_api.find_or_create_user_from_github(db, github_user, emails)

        assert is_new is True
        assert user.first_name == "New"
        assert user.last_name == "GitHub User"
        assert user.email == "new@github.com"
        assert user.oauth_accounts["github"]["id"] == "11111"

    async def test_finds_existing_by_email(self, db, oauth_api):
        # Create existing user
        existing = User(
            first_name="Existing",
            last_name="User",
            email="existing@github.com",
            is_active=True,
        )
        db.add(existing)
        await db.flush()

        github_user = {"id": 22222, "login": "existinggh"}
        emails = [{"email": "existing@github.com", "primary": True, "verified": True}]

        user, is_new = await oauth_api.find_or_create_user_from_github(db, github_user, emails)

        assert is_new is False
        assert user.id == existing.id
        assert user.oauth_accounts["github"]["id"] == "22222"

    async def test_finds_existing_by_github_id(self, db, oauth_api):
        existing = User(
            first_name="GH",
            last_name="User",
            email="ghid@test.com",
            is_active=True,
            oauth_accounts={"github": {"id": "33333", "login": "oldlogin"}},
        )
        db.add(existing)
        await db.flush()

        github_user = {"id": 33333, "login": "newlogin"}
        emails = [{"email": "diff@github.com", "primary": True, "verified": True}]

        user, is_new = await oauth_api.find_or_create_user_from_github(db, github_user, emails)

        assert is_new is False
        assert user.id == existing.id
        assert user.oauth_accounts["github"]["login"] == "newlogin"
