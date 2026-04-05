"""add task_id to jobs

Revision ID: b3e8f2a91c04
Revises: 41d879a25969
Create Date: 2026-04-04 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e8f2a91c04"
down_revision: Union[str, None] = "41d879a25969"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("task_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_jobs_task_id"), "jobs", ["task_id"], unique=False)
    op.create_foreign_key("fk_jobs_task_id_tasks", "jobs", "tasks", ["task_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_jobs_task_id_tasks", "jobs", type_="foreignkey")
    op.drop_index(op.f("ix_jobs_task_id"), table_name="jobs")
    op.drop_column("jobs", "task_id")
