"""add_users_connections

Revision ID: 0bdc598a80f6
Revises: 06f1d07766f4
Create Date: 2026-03-24 22:10:57.928531

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0bdc598a80f6'
down_revision: Union[str, None] = '06f1d07766f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users table (from pattern_stack.features.users.models.User) ---
    # Skip if already created by a8a10495d2b9
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"))
    users_exists = result.scalar()
    if not users_exists:
        op.create_table('users',
            sa.Column('first_name', sa.String(length=100), nullable=False, comment="User's first name"),
            sa.Column('last_name', sa.String(length=100), nullable=False, comment="User's last name"),
            sa.Column('password_hash', sa.String(length=255), nullable=True, comment='Hashed password (nullable for OAuth-only users)'),
            sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether user is active'),
            sa.Column('oauth_accounts', sa.JSON(), nullable=False, comment='OAuth account links (provider -> account_id mapping)'),
            sa.Column('display_name', sa.String(length=255), nullable=False, comment='Display name for the actor'),
            sa.Column('actor_type', sa.String(length=50), nullable=False, comment='Type of actor (user, organization, system, service)'),
            sa.Column('email', sa.String(length=320), nullable=True, comment='Email address for contactable actors'),
            sa.Column('phone', sa.String(length=20), nullable=True, comment='Phone number for contactable actors'),
            sa.Column('profile_data', sa.JSON(), nullable=False, comment='Flexible profile information'),
            sa.Column('external_id', sa.String(length=100), nullable=True, comment='Reference to external system'),
            sa.Column('integration_metadata', sa.JSON(), nullable=False, comment='Integration-specific data'),
            sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp of last activity'),
            sa.Column('activity_count', sa.Integer(), nullable=False, comment='Number of actions performed'),
            sa.Column('reference_number', sa.String(length=50), nullable=True, comment='Unique reference number'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_actor_type'), 'users', ['actor_type'], unique=False)
        op.create_index(op.f('ix_users_display_name'), 'users', ['display_name'], unique=False)
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
        op.create_index(op.f('ix_users_external_id'), 'users', ['external_id'], unique=False)
        op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
        op.create_index(op.f('ix_users_reference_number'), 'users', ['reference_number'], unique=True)

    # --- connections table (from pattern_stack.atoms.integrations.models.Connection) ---
    op.create_table('connections',
    sa.Column('provider', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('webhook_path', sa.String(length=100), nullable=False),
    sa.Column('config_encrypted', sa.LargeBinary(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=True),
    sa.Column('team_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('webhook_secret', sa.String(length=200), nullable=True),
    sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_error', sa.String(length=2000), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.CheckConstraint("webhook_path ~ '^[a-zA-Z0-9][a-zA-Z0-9_-]*$'", name='ck_connection_webhook_path_valid'),
    sa.CheckConstraint('LENGTH(config_encrypted) <= 65536', name='ck_connection_config_size'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('webhook_path')
    )
    op.create_index(op.f('ix_connections_enabled'), 'connections', ['enabled'], unique=False)
    op.create_index(op.f('ix_connections_provider'), 'connections', ['provider'], unique=False)
    op.create_index(op.f('ix_connections_status'), 'connections', ['status'], unique=False)
    op.create_index(op.f('ix_connections_team_id'), 'connections', ['team_id'], unique=False)

    # --- sync_records table (from pattern_stack.atoms.integrations.models.SyncRecord) ---
    op.create_table('sync_records',
    sa.Column('id', sa.UUID(), nullable=False, comment='Sync record identifier'),
    sa.Column('entity_type', sa.String(length=100), nullable=False, comment="Model class name (e.g., 'Contact', 'Deal')"),
    sa.Column('entity_id', sa.UUID(), nullable=False, comment="Local entity's primary key"),
    sa.Column('connection_id', sa.UUID(), nullable=False, comment='Connection this sync is through'),
    sa.Column('external_id', sa.String(length=255), nullable=False, comment='ID in the external system'),
    sa.Column('last_job_id', sa.UUID(), nullable=True, comment='Job that last synced this entity (no FK for table independence)'),
    sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True, comment='When entity was last successfully synced'),
    sa.Column('status', sa.String(length=20), nullable=False, comment='Sync status: pending, synced, error'),
    sa.Column('last_error', sa.Text(), nullable=True, comment='Error message from last failed sync'),
    sa.Column('error_count', sa.Integer(), nullable=False, comment='Consecutive sync failure count'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When the sync record was created'),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='When the sync record was last modified'),
    sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('entity_type', 'entity_id', 'connection_id', name='uq_sync_record_entity_connection')
    )
    op.create_index(op.f('ix_sync_records_connection_id'), 'sync_records', ['connection_id'], unique=False)
    op.create_index('ix_sync_records_connection_status', 'sync_records', ['connection_id', 'status'], unique=False)
    op.create_index('ix_sync_records_connection_status_time', 'sync_records', ['connection_id', 'status', 'synced_at'], unique=False)
    op.create_index('ix_sync_records_entity_type', 'sync_records', ['entity_type'], unique=False)
    op.create_index('ix_sync_records_external', 'sync_records', ['connection_id', 'external_id'], unique=False)

    # --- webhook_events table (from pattern_stack.atoms.integrations.models.WebhookEvent) ---
    op.create_table('webhook_events',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False, comment='Webhook event identifier'),
    sa.Column('connection_id', sa.UUID(), nullable=False, comment='Connection that received this webhook'),
    sa.Column('webhook_id', sa.String(length=200), nullable=False, comment='Unique webhook ID from provider (for deduplication)'),
    sa.Column('event_type', sa.String(length=100), nullable=False, comment="Provider event type (e.g., 'issue.updated')"),
    sa.Column('payload_hash', sa.String(length=64), nullable=True, comment='SHA256 of payload (for debugging)'),
    sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When webhook was received'),
    sa.Column('status', sa.String(length=20), nullable=False, comment='Status: received, queued, processing, completed, failed'),
    sa.Column('job_id', sa.UUID(), nullable=True, comment='Reference to queued job (no FK for independence)'),
    sa.Column('error_message', sa.Text(), nullable=True, comment='Error details if processing failed'),
    sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('connection_id', 'webhook_id', name='uq_webhook_event_idempotency')
    )
    op.create_index(op.f('ix_webhook_events_connection_id'), 'webhook_events', ['connection_id'], unique=False)
    op.create_index('ix_webhook_events_received_at', 'webhook_events', ['received_at'], unique=False)
    op.create_index('ix_webhook_events_status', 'webhook_events', ['status'], unique=False)

    # --- job_records table (from pattern_stack.atoms.jobs) ---
    op.create_table('job_records',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False, comment='Job identifier'),
    sa.Column('job_type', sa.String(length=100), nullable=False, comment="Job type like 'integration.sync_outbound'"),
    sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=False, comment='Job-specific data'),
    sa.Column('status', sa.String(length=20), nullable=False, comment='Job status: pending, running, completed, failed, retrying, dead'),
    sa.Column('priority', sa.Integer(), nullable=False, comment='Job priority (higher = more urgent)'),
    sa.Column('attempts', sa.Integer(), nullable=False, comment='Number of execution attempts'),
    sa.Column('max_retries', sa.Integer(), nullable=False, comment='Maximum retry attempts before marking as dead'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When the job was created/enqueued'),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='When the job was last modified'),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='When job execution started'),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='When job execution finished'),
    sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Job result data if successful'),
    sa.Column('error', sa.Text(), nullable=True, comment='Error message if failed'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_job_records_completed_at', 'job_records', ['completed_at'], unique=False)
    op.create_index('ix_job_records_created_at', 'job_records', ['created_at'], unique=False)
    op.create_index('ix_job_records_dequeue', 'job_records', ['status', 'priority', 'created_at'], unique=False)
    op.create_index(op.f('ix_job_records_job_type'), 'job_records', ['job_type'], unique=False)
    op.create_index('ix_job_records_type_status', 'job_records', ['job_type', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_job_records_type_status', table_name='job_records')
    op.drop_index(op.f('ix_job_records_job_type'), table_name='job_records')
    op.drop_index('ix_job_records_dequeue', table_name='job_records')
    op.drop_index('ix_job_records_created_at', table_name='job_records')
    op.drop_index('ix_job_records_completed_at', table_name='job_records')
    op.drop_table('job_records')

    op.drop_index('ix_webhook_events_status', table_name='webhook_events')
    op.drop_index('ix_webhook_events_received_at', table_name='webhook_events')
    op.drop_index(op.f('ix_webhook_events_connection_id'), table_name='webhook_events')
    op.drop_table('webhook_events')

    op.drop_index('ix_sync_records_external', table_name='sync_records')
    op.drop_index('ix_sync_records_entity_type', table_name='sync_records')
    op.drop_index('ix_sync_records_connection_status_time', table_name='sync_records')
    op.drop_index('ix_sync_records_connection_status', table_name='sync_records')
    op.drop_index(op.f('ix_sync_records_connection_id'), table_name='sync_records')
    op.drop_table('sync_records')

    op.drop_index(op.f('ix_connections_team_id'), table_name='connections')
    op.drop_index(op.f('ix_connections_status'), table_name='connections')
    op.drop_index(op.f('ix_connections_provider'), table_name='connections')
    op.drop_index(op.f('ix_connections_enabled'), table_name='connections')
    op.drop_table('connections')

    op.drop_index(op.f('ix_users_reference_number'), table_name='users')
    op.drop_index(op.f('ix_users_is_active'), table_name='users')
    op.drop_index(op.f('ix_users_external_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_display_name'), table_name='users')
    op.drop_index(op.f('ix_users_actor_type'), table_name='users')
    op.drop_table('users')
