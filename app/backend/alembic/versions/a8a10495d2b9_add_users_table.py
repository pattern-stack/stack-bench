"""add users table

Revision ID: a8a10495d2b9
Revises: c1f0f154b442
Create Date: 2026-03-24 22:32:25.599396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a8a10495d2b9'
down_revision: Union[str, None] = 'c1f0f154b442'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Skip if users table already exists (may be created by 0bdc598a80f6)
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"))
    if result.scalar():
        return
    op.create_table(
        'users',
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('oauth_accounts', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('actor_type', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('profile_data', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('external_id', sa.String(length=100), nullable=True),
        sa.Column('integration_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activity_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('reference_number', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('reference_number'),
    )


def downgrade() -> None:
    op.drop_table('users')
