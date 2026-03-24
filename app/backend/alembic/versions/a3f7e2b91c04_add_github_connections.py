"""add github_connections

Revision ID: a3f7e2b91c04
Revises: 1505160361ec
Create Date: 2026-03-24 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f7e2b91c04"
down_revision: str | None = "1505160361ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "github_connections",
        sa.Column("github_user_id", sa.Integer(), nullable=False),
        sa.Column("github_login", sa.String(length=255), nullable=False),
        sa.Column("tokens_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_github_connections_github_user_id"),
        "github_connections",
        ["github_user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_github_connections_github_user_id"), table_name="github_connections")
    op.drop_table("github_connections")
