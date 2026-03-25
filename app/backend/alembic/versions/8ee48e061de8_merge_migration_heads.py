"""merge migration heads

Revision ID: 8ee48e061de8
Revises: 20cb22b7ab0f, a3f7c8d91e42
Create Date: 2026-03-24 23:42:17.360593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ee48e061de8'
down_revision: Union[str, None] = ('20cb22b7ab0f', 'a3f7c8d91e42')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
