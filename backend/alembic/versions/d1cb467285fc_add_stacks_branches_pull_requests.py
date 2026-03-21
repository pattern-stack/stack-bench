"""add stacks branches pull requests

Revision ID: d1cb467285fc
Revises: ec4e248f15f5
Create Date: 2026-03-20 13:51:48.793510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1cb467285fc'
down_revision: Union[str, None] = 'ec4e248f15f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create stacks table WITHOUT base_branch_id FK (circular dependency)
    op.create_table('stacks',
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('base_branch_id', sa.UUID(), nullable=True),
        sa.Column('trunk', sa.String(length=200), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, comment='Current state in the state machine'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when the record was soft deleted'),
        sa.Column('reference_number', sa.String(length=50), nullable=True, comment='Unique reference number'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stacks_project_id'), 'stacks', ['project_id'], unique=False)
    op.create_index(op.f('ix_stacks_name'), 'stacks', ['name'], unique=False)
    op.create_index(op.f('ix_stacks_base_branch_id'), 'stacks', ['base_branch_id'], unique=False)
    op.create_index(op.f('ix_stacks_state'), 'stacks', ['state'], unique=False)
    op.create_index(op.f('ix_stacks_reference_number'), 'stacks', ['reference_number'], unique=True)

    # Step 2: Create branches table with stack_id FK -> stacks.id
    op.create_table('branches',
        sa.Column('stack_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('head_sha', sa.String(length=40), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, comment='Current state in the state machine'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when the record was soft deleted'),
        sa.Column('reference_number', sa.String(length=50), nullable=True, comment='Unique reference number'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.ForeignKeyConstraint(['stack_id'], ['stacks.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stack_id', 'position', name='uq_branch_stack_position')
    )
    op.create_index(op.f('ix_branches_stack_id'), 'branches', ['stack_id'], unique=False)
    op.create_index(op.f('ix_branches_workspace_id'), 'branches', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_branches_state'), 'branches', ['state'], unique=False)
    op.create_index(op.f('ix_branches_reference_number'), 'branches', ['reference_number'], unique=True)

    # Step 3: Create pull_requests table with branch_id FK -> branches.id
    op.create_table('pull_requests',
        sa.Column('branch_id', sa.UUID(), nullable=False),
        sa.Column('external_id', sa.Integer(), nullable=True),
        sa.Column('external_url', sa.String(length=500), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, comment='Current state in the state machine'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when the record was soft deleted'),
        sa.Column('reference_number', sa.String(length=50), nullable=True, comment='Unique reference number'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('branch_id')
    )
    op.create_index(op.f('ix_pull_requests_branch_id'), 'pull_requests', ['branch_id'], unique=True)
    op.create_index(op.f('ix_pull_requests_state'), 'pull_requests', ['state'], unique=False)
    op.create_index(op.f('ix_pull_requests_reference_number'), 'pull_requests', ['reference_number'], unique=True)

    # Step 4: Add deferred FK from stacks.base_branch_id -> branches.id
    op.create_foreign_key(
        "fk_stacks_base_branch_id",
        "stacks",
        "branches",
        ["base_branch_id"],
        ["id"],
    )

    # Step 5: SKIPPED — worktrees table does not exist yet (SB-034 not built).
    # When SB-034 is built, it will add the worktrees.branch_id FK -> branches.id.


def downgrade() -> None:
    # Step 4: Drop deferred FK from stacks.base_branch_id
    op.drop_constraint("fk_stacks_base_branch_id", "stacks", type_="foreignkey")

    # Step 3: Drop pull_requests
    op.drop_index(op.f('ix_pull_requests_reference_number'), table_name='pull_requests')
    op.drop_index(op.f('ix_pull_requests_state'), table_name='pull_requests')
    op.drop_index(op.f('ix_pull_requests_branch_id'), table_name='pull_requests')
    op.drop_table('pull_requests')

    # Step 2: Drop branches
    op.drop_index(op.f('ix_branches_reference_number'), table_name='branches')
    op.drop_index(op.f('ix_branches_state'), table_name='branches')
    op.drop_index(op.f('ix_branches_workspace_id'), table_name='branches')
    op.drop_index(op.f('ix_branches_stack_id'), table_name='branches')
    op.drop_table('branches')

    # Step 1: Drop stacks
    op.drop_index(op.f('ix_stacks_reference_number'), table_name='stacks')
    op.drop_index(op.f('ix_stacks_state'), table_name='stacks')
    op.drop_index(op.f('ix_stacks_base_branch_id'), table_name='stacks')
    op.drop_index(op.f('ix_stacks_name'), table_name='stacks')
    op.drop_index(op.f('ix_stacks_project_id'), table_name='stacks')
    op.drop_table('stacks')
