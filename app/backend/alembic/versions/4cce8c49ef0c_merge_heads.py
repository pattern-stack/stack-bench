"""merge heads

Revision ID: 4cce8c49ef0c
Revises: 1505160361ec, 89e145f87ff2
Create Date: 2026-03-24 00:31:14.502706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cce8c49ef0c'
down_revision: Union[str, None] = ('1505160361ec', '89e145f87ff2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
