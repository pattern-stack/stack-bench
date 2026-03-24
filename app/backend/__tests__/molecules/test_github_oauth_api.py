import hashlib
import base64
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from molecules.apis.github_oauth_api import GitHubOAuthAPI, _pending_oauth

# Generate a stable test Fernet key
_TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def clear_pending_oauth() -> None:
    """Clear pending OAuth state between tests."""
    _pending_oauth.clear()


def _mock_connection() -> MagicMock:
    """Create a mock GitHubConnection with valid fields."""
    conn = MagicMock()
    conn.id = uuid4()
    conn.github_user_id = 12345
    conn.github_login = "testuser"
    conn.token_expires_at = datetime(2026, 3, 25, tzinfo=timezone.utc)
    conn.connected = True
    conn.created_at = datetime(2026, 3, 24, tzinfo=timezone.utc)
    conn.updated_at = datetime(2026, 3, 24, tzinfo=timezone.utc)
    return conn


@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.GITHUB_APP_CLIENT_ID = "test-client-id"
    settings.GITHUB_APP_CLIENT_SECRET = "test-client-secret"
    settings.GITHUB_OAUTH_REDIRECT_URI = "http://localhost:8500/api/v1/auth/github/callback"
    settings.FRONTEND_URL = "http://localhost:3500"
    settings.ENCRYPTION_KEY = _TEST_FERNET_KEY
    return settings


@pytest.fixture
def oauth_api(mock_settings: MagicMock) -> GitHubOAuthAPI:
    db = AsyncMock()
    with patch("molecules.apis.github_oauth_api.get_settings", return_value=mock_settings):
        api = GitHubOAuthAPI(db)
    return api


@pytest.mark.unit
def test_oauth_api_init() -> None:
    """Verify GitHubOAuthAPI composes GitHubConnectionService."""
    db = AsyncMock()
    api = GitHubOAuthAPI(db)
    assert hasattr(api, "service")
    assert hasattr(api, "settings")
    assert hasattr(api, "db")


@pytest.mark.unit
def test_build_authorize_url_returns_url_and_state(oauth_api: GitHubOAuthAPI) -> None:
    """Verify build_authorize_url returns a tuple of (url, state)."""
    code_verifier = "test-verifier-that-is-at-least-43-characters-long-abc"
    url, state = oauth_api.build_authorize_url(code_verifier)
    assert isinstance(url, str)
    assert isinstance(state, str)
    assert "github.com" in url
    assert "authorize" in url


@pytest.mark.unit
def test_build_authorize_url_contains_pkce_params(oauth_api: GitHubOAuthAPI) -> None:
    """Verify URL contains code_challenge and code_challenge_method=S256."""
    code_verifier = "test-verifier-that-is-at-least-43-characters-long-abc"
    url, _state = oauth_api.build_authorize_url(code_verifier)
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert "client_id=test-client-id" in url
    assert "redirect_uri=" in url


@pytest.mark.unit
def test_build_authorize_url_correct_s256_challenge(oauth_api: GitHubOAuthAPI) -> None:
    """Verify PKCE S256 challenge is computed correctly per RFC 7636."""
    code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    url, _state = oauth_api.build_authorize_url(code_verifier)

    # Compute expected challenge
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    assert f"code_challenge={expected_challenge}" in url


@pytest.mark.unit
def test_build_authorize_url_unique_state(oauth_api: GitHubOAuthAPI) -> None:
    """Verify each call generates unique state."""
    verifier = "test-verifier-that-is-at-least-43-characters-long-abc"
    _, state1 = oauth_api.build_authorize_url(verifier)
    _, state2 = oauth_api.build_authorize_url(verifier)
    assert state1 != state2


@pytest.mark.unit
def test_build_authorize_url_stores_state(oauth_api: GitHubOAuthAPI) -> None:
    """Verify state -> code_verifier is stored for callback retrieval."""
    code_verifier = "test-verifier-that-is-at-least-43-characters-long-abc"
    _, state = oauth_api.build_authorize_url(code_verifier)
    assert state in _pending_oauth
    stored_verifier, _expires = _pending_oauth[state]
    assert stored_verifier == code_verifier


@pytest.mark.unit
def test_state_store_has_ttl(oauth_api: GitHubOAuthAPI) -> None:
    """Verify stored state has an expiry timestamp in the future."""
    code_verifier = "test-verifier-that-is-at-least-43-characters-long-abc"
    _, state = oauth_api.build_authorize_url(code_verifier)
    _verifier, expires_at = _pending_oauth[state]
    assert expires_at > time.time()
    # Should expire within ~10 minutes
    assert expires_at < time.time() + 700


@pytest.mark.unit
async def test_handle_callback_exchanges_code(oauth_api: GitHubOAuthAPI) -> None:
    """Verify handle_callback calls GitHub token endpoint with correct params."""
    code_verifier = "test-verifier-that-is-at-least-43-characters-long-abc"
    _, state = oauth_api.build_authorize_url(code_verifier)

    mock_token_response = MagicMock()
    mock_token_response.json.return_value = {
        "access_token": "ghu_test_token",
        "refresh_token": "ghr_test_refresh",
        "expires_in": 28800,
        "refresh_token_expires_in": 15768000,
        "token_type": "bearer",
    }
    mock_token_response.raise_for_status = MagicMock()

    mock_user_response = MagicMock()
    mock_user_response.json.return_value = {
        "id": 12345,
        "login": "testuser",
    }
    mock_user_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post.return_value = mock_token_response
    mock_client.get.return_value = mock_user_response

    # Mock the service upsert
    oauth_api.service.upsert = AsyncMock(return_value=_mock_connection())

    with patch("molecules.apis.github_oauth_api.httpx.AsyncClient", return_value=mock_client):
        result = await oauth_api.handle_callback("test-code", state)

    # Verify token endpoint was called
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert "github.com" in call_kwargs[0][0] or "github.com" in str(call_kwargs)


@pytest.mark.unit
async def test_handle_callback_invalid_state(oauth_api: GitHubOAuthAPI) -> None:
    """Verify handle_callback raises on invalid/unknown state."""
    with pytest.raises(ValueError, match="state"):
        await oauth_api.handle_callback("test-code", "invalid-state")


@pytest.mark.unit
async def test_handle_callback_expired_state(oauth_api: GitHubOAuthAPI) -> None:
    """Verify handle_callback raises on expired state."""
    # Manually insert an expired state
    _pending_oauth["expired-state"] = ("verifier", time.time() - 100)
    with pytest.raises(ValueError, match="expired"):
        await oauth_api.handle_callback("test-code", "expired-state")


@pytest.mark.unit
async def test_handle_callback_encrypts_tokens(oauth_api: GitHubOAuthAPI) -> None:
    """Verify tokens are encrypted before storage."""
    code_verifier = "test-verifier-that-is-at-least-43-characters-long-abc"
    _, state = oauth_api.build_authorize_url(code_verifier)

    mock_token_response = MagicMock()
    mock_token_response.json.return_value = {
        "access_token": "ghu_test_token",
        "refresh_token": "ghr_test_refresh",
        "expires_in": 28800,
        "refresh_token_expires_in": 15768000,
        "token_type": "bearer",
    }
    mock_token_response.raise_for_status = MagicMock()

    mock_user_response = MagicMock()
    mock_user_response.json.return_value = {
        "id": 12345,
        "login": "testuser",
    }
    mock_user_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post.return_value = mock_token_response
    mock_client.get.return_value = mock_user_response

    # Capture what gets passed to upsert
    captured_data = None

    async def capture_upsert(db: object, data: object) -> MagicMock:
        nonlocal captured_data
        captured_data = data
        return _mock_connection()

    oauth_api.service.upsert = capture_upsert  # type: ignore[assignment]

    with patch("molecules.apis.github_oauth_api.httpx.AsyncClient", return_value=mock_client):
        await oauth_api.handle_callback("test-code", state)

    # Verify the tokens_encrypted field is actually encrypted
    assert captured_data is not None
    assert captured_data.tokens_encrypted != b""
    # Should be decryptable with the Fernet key
    fernet_key = _TEST_FERNET_KEY.encode()
    f = Fernet(fernet_key)
    decrypted = json.loads(f.decrypt(captured_data.tokens_encrypted))
    assert decrypted["access_token"] == "ghu_test_token"
    assert decrypted["refresh_token"] == "ghr_test_refresh"


@pytest.mark.unit
async def test_get_connection_status_none(oauth_api: GitHubOAuthAPI) -> None:
    """Verify get_connection_status returns None when no connection."""
    oauth_api.service.list = AsyncMock(return_value=([], 0))
    result = await oauth_api.get_connection_status()
    assert result is None


@pytest.mark.unit
async def test_get_connection_status_connected(oauth_api: GitHubOAuthAPI) -> None:
    """Verify get_connection_status returns response when connected."""
    mock_conn = _mock_connection()
    oauth_api.service.list = AsyncMock(return_value=([mock_conn], 1))
    result = await oauth_api.get_connection_status()
    assert result is not None
    assert result.github_login == "testuser"
    assert result.connected is True


@pytest.mark.unit
def test_cleanup_expired_state(oauth_api: GitHubOAuthAPI) -> None:
    """Verify expired entries are cleaned from the state store."""
    from molecules.apis.github_oauth_api import cleanup_expired_state

    # Add some entries -- one expired, one not
    _pending_oauth["expired"] = ("verifier1", time.time() - 100)
    _pending_oauth["valid"] = ("verifier2", time.time() + 600)

    cleanup_expired_state()

    assert "expired" not in _pending_oauth
    assert "valid" in _pending_oauth
