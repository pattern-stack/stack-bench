"""add conversation_type to conversations

Revision ID: a1f2c3d4e5f6
Revises: b3e8f2a91c04
Create Date: 2026-04-05 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f2c3d4e5f6"
down_revision: Union[str, None] = "b3e8f2a91c04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("conversation_type", sa.String(20), nullable=False, server_default="execution"),
    )
    op.create_index(
        op.f("ix_conversations_conversation_type"),
        "conversations",
        ["conversation_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conversations_conversation_type"), table_name="conversations")
    op.drop_column("conversations", "conversation_type")
