"""add review_comments table

Revision ID: 89e145f87ff2
Revises: d1cb467285fc
Create Date: 2026-03-22 23:13:31.064041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89e145f87ff2'
down_revision: Union[str, None] = 'd1cb467285fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('review_comments',
    sa.Column('pull_request_id', sa.UUID(), nullable=False),
    sa.Column('branch_id', sa.UUID(), nullable=False),
    sa.Column('path', sa.String(length=500), nullable=False),
    sa.Column('line_key', sa.String(length=200), nullable=False),
    sa.Column('line_number', sa.Integer(), nullable=True),
    sa.Column('side', sa.String(length=10), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('author', sa.String(length=200), nullable=False),
    sa.Column('external_id', sa.Integer(), nullable=True),
    sa.Column('resolved', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
    sa.ForeignKeyConstraint(['pull_request_id'], ['pull_requests.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_review_comments_branch_id'), 'review_comments', ['branch_id'], unique=False)
    op.create_index(op.f('ix_review_comments_pull_request_id'), 'review_comments', ['pull_request_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_review_comments_pull_request_id'), table_name='review_comments')
    op.drop_index(op.f('ix_review_comments_branch_id'), table_name='review_comments')
    op.drop_table('review_comments')
