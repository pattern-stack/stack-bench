"""add conversation_links table

Revision ID: b2a3c4d5e6f7
Revises: a1f2c3d4e5f6
Create Date: 2026-04-05 10:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2a3c4d5e6f7"
down_revision: Union[str, None] = "a1f2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference_number", sa.String(50), nullable=True),
        sa.Column("entity_a_type", sa.String(100), nullable=False),
        sa.Column("entity_a_id", sa.Uuid(), nullable=False),
        sa.Column("entity_b_type", sa.String(100), nullable=False),
        sa.Column("entity_b_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("relationship_metadata", sa.JSON(), nullable=True, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_links_entity_a", "conversation_links", ["entity_a_type", "entity_a_id"])
    op.create_index("ix_conversation_links_entity_b", "conversation_links", ["entity_b_type", "entity_b_id"])
    op.create_index("ix_conversation_links_relationship_type", "conversation_links", ["relationship_type"])
    op.create_index("ix_conversation_links_is_active", "conversation_links", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_conversation_links_is_active", table_name="conversation_links")
    op.drop_index("ix_conversation_links_relationship_type", table_name="conversation_links")
    op.drop_index("ix_conversation_links_entity_b", table_name="conversation_links")
    op.drop_index("ix_conversation_links_entity_a", table_name="conversation_links")
    op.drop_table("conversation_links")
