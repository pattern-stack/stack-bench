"""merge all heads

Revision ID: b1a2c3d4e5f6
Revises: 0bdc598a80f6, 8ee48e061de8, a8a10495d2b9
Create Date: 2026-03-25 10:00:00.000000

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, None] = ("0bdc598a80f6", "8ee48e061de8", "a8a10495d2b9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
