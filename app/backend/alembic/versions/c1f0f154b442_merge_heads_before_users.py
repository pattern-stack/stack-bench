"""merge heads before users

Revision ID: c1f0f154b442
Revises: 20cb22b7ab0f, a3f7c8d91e42
Create Date: 2026-03-24 22:32:18.924646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f0f154b442'
down_revision: Union[str, None] = ('20cb22b7ab0f', 'a3f7c8d91e42')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
