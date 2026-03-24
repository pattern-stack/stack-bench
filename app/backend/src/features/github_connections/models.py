from datetime import datetime

from pattern_stack.atoms.patterns import BasePattern, Field


class GitHubConnection(BasePattern):
    __tablename__ = "github_connections"

    class Pattern:
        entity = "github_connection"
        reference_prefix = "GHC"
        track_changes = True

    # GitHub user identity
    github_user_id = Field(int, required=True, unique=True, index=True)
    github_login = Field(str, required=True, max_length=255)

    # Encrypted tokens (Fernet-encrypted JSON blob containing
    # access_token, refresh_token, expires_at, refresh_expires_at)
    tokens_encrypted = Field(bytes, required=True)

    # Token metadata (unencrypted for query/monitoring)
    token_expires_at = Field(datetime, nullable=True)
    refresh_token_expires_at = Field(datetime, nullable=True)
