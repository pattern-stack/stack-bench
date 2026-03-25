"""add project owner_id and make local_path nullable

Revision ID: c2b3a4d5e6f7
Revises: b1a2c3d4e5f6
Create Date: 2026-03-25 10:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2b3a4d5e6f7"
down_revision: Union[str, None] = "b1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add owner_id column (nullable first for existing rows)
    op.add_column("projects", sa.Column("owner_id", sa.UUID(), nullable=True))

    # For existing projects, set owner_id to the first user (dev convenience)
    op.execute(
        "UPDATE projects SET owner_id = (SELECT id FROM users LIMIT 1) WHERE owner_id IS NULL"
    )

    # Make owner_id NOT NULL after backfill
    op.alter_column("projects", "owner_id", nullable=False)

    # Add FK and index
    op.create_foreign_key(
        "fk_projects_owner_id_users",
        "projects",
        "users",
        ["owner_id"],
        ["id"],
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)

    # Make local_path nullable
    op.alter_column(
        "projects",
        "local_path",
        existing_type=sa.String(length=500),
        nullable=True,
    )


def downgrade() -> None:
    # Make local_path NOT NULL again
    op.alter_column(
        "projects",
        "local_path",
        existing_type=sa.String(length=500),
        nullable=False,
    )

    # Drop owner_id
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_constraint("fk_projects_owner_id_users", "projects", type_="foreignkey")
    op.drop_column("projects", "owner_id")
