from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from features.github_connections.models import GitHubConnection
from features.github_connections.schemas.input import (
    GitHubConnectionCreate,
    GitHubConnectionUpdate,
)
from features.github_connections.schemas.output import GitHubConnectionResponse
from features.github_connections.service import GitHubConnectionService


@pytest.mark.unit
def test_github_connection_model_fields() -> None:
    """Verify model has expected domain fields."""
    assert hasattr(GitHubConnection, "github_user_id")
    assert hasattr(GitHubConnection, "github_login")
    assert hasattr(GitHubConnection, "tokens_encrypted")
    assert hasattr(GitHubConnection, "token_expires_at")
    assert hasattr(GitHubConnection, "refresh_token_expires_at")


@pytest.mark.unit
def test_github_connection_pattern_config() -> None:
    """Verify Pattern inner class is configured correctly."""
    assert GitHubConnection.Pattern.entity == "github_connection"
    assert GitHubConnection.Pattern.reference_prefix == "GHC"
    assert GitHubConnection.Pattern.track_changes is True


@pytest.mark.unit
def test_github_connection_is_base_pattern() -> None:
    """Verify GitHubConnection uses BasePattern (no state machine)."""
    from pattern_stack.atoms.patterns import BasePattern

    assert issubclass(GitHubConnection, BasePattern)
    assert not hasattr(GitHubConnection.Pattern, "states") or not GitHubConnection.Pattern.states


@pytest.mark.unit
def test_create_schema_valid() -> None:
    """Verify create schema with all required fields."""
    data = GitHubConnectionCreate(
        github_user_id=12345,
        github_login="testuser",
        tokens_encrypted=b"encrypted-token-data",
        token_expires_at=datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc),
        refresh_token_expires_at=datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert data.github_user_id == 12345
    assert data.github_login == "testuser"
    assert data.tokens_encrypted == b"encrypted-token-data"


@pytest.mark.unit
def test_create_schema_required_fields() -> None:
    """Verify required fields are enforced."""
    with pytest.raises(ValidationError):
        GitHubConnectionCreate()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        GitHubConnectionCreate(github_user_id=123)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        GitHubConnectionCreate(github_user_id=123, github_login="test")  # type: ignore[call-arg]


@pytest.mark.unit
def test_create_schema_optional_expiry() -> None:
    """Verify expiry fields are optional."""
    data = GitHubConnectionCreate(
        github_user_id=12345,
        github_login="testuser",
        tokens_encrypted=b"encrypted-token-data",
    )
    assert data.token_expires_at is None
    assert data.refresh_token_expires_at is None


@pytest.mark.unit
def test_update_schema_partial() -> None:
    """Verify update schema allows partial updates."""
    data = GitHubConnectionUpdate(github_login="newlogin")
    assert data.github_login == "newlogin"
    assert data.tokens_encrypted is None
    assert data.token_expires_at is None
    assert data.refresh_token_expires_at is None


@pytest.mark.unit
def test_update_schema_all_fields() -> None:
    """Verify update schema accepts all updatable fields."""
    data = GitHubConnectionUpdate(
        tokens_encrypted=b"new-encrypted-data",
        github_login="newlogin",
        token_expires_at=datetime(2026, 3, 25, 12, 0, 0, tzinfo=timezone.utc),
        refresh_token_expires_at=datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert data.tokens_encrypted == b"new-encrypted-data"
    assert data.github_login == "newlogin"


@pytest.mark.unit
def test_response_schema_excludes_tokens() -> None:
    """Verify response schema does NOT include tokens_encrypted."""
    fields = GitHubConnectionResponse.model_fields
    assert "tokens_encrypted" not in fields
    assert "github_user_id" in fields
    assert "github_login" in fields
    assert "connected" in fields


@pytest.mark.unit
def test_response_schema_from_attributes() -> None:
    """Verify response schema has from_attributes config."""
    assert GitHubConnectionResponse.model_config.get("from_attributes") is True


@pytest.mark.unit
def test_response_schema_connected_default() -> None:
    """Verify connected field defaults to True."""
    from uuid import uuid4

    resp = GitHubConnectionResponse(
        id=uuid4(),
        github_user_id=123,
        github_login="test",
        created_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
    )
    assert resp.connected is True


@pytest.mark.unit
def test_service_model() -> None:
    """Verify service is configured with correct model."""
    service = GitHubConnectionService()
    assert service.model is GitHubConnection
