"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Tenants
    op.create_table('tenants',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('plan', sa.String(20), server_default='free'),
        sa.Column('branding', sa.JSON(), server_default='{}'),
        sa.Column('feature_flags', sa.JSON(), server_default='{}'),
        sa.Column('custom_domain', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Users
    op.create_table('users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('role', sa.String(20), server_default='member'),
        sa.Column('preferences', sa.JSON(), server_default='{}'),
        sa.Column('onboarding_completed', sa.Boolean(), server_default='false'),
        sa.Column('onboarding_step', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_active_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_tenant', 'users', ['tenant_id'])

    # Conversations
    op.create_table('conversations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), server_default='New Conversation'),
        sa.Column('pinned', sa.Boolean(), server_default='false'),
        sa.Column('archived', sa.Boolean(), server_default='false'),
        sa.Column('message_count', sa.Integer(), server_default='0'),
        sa.Column('parent_id', sa.String(), nullable=True),  # For conversation branching
        sa.Column('branch_point_msg_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_conversations_user', 'conversations', ['user_id'])

    # Chat Messages
    op.create_table('chat_messages',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('conversation_id', sa.String(), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_messages_conversation', 'chat_messages', ['conversation_id'])

    # Integrations
    op.create_table('integrations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), server_default='disconnected'),
        sa.Column('config', sa.JSON(), server_default='{}'),
        sa.Column('oauth_token', sa.Text(), nullable=True),
        sa.Column('oauth_refresh_token', sa.Text(), nullable=True),
        sa.Column('oauth_expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_integrations_user', 'integrations', ['user_id'])

    # Memories
    op.create_table('memories',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(255), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='1.0'),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_accessed_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_memories_user', 'memories', ['user_id'])

    # Projects
    op.create_table('projects',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('integration_id', sa.String(), sa.ForeignKey('integrations.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('tech_stack', sa.JSON(), server_default='[]'),
        sa.Column('modules', sa.JSON(), server_default='[]'),
        sa.Column('health_score', sa.Integer(), nullable=True),
        sa.Column('last_analyzed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Standing Orders
    op.create_table('standing_orders',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trigger_type', sa.String(20), nullable=False),
        sa.Column('trigger_config', sa.JSON(), server_default='{}'),
        sa.Column('actions', sa.JSON(), server_default='[]'),
        sa.Column('enabled', sa.Boolean(), server_default='true'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('run_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_standing_orders_user', 'standing_orders', ['user_id'])

    # Approval Requests
    op.create_table('approval_requests',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('tier', sa.String(20), nullable=False),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tool_name', sa.String(100), nullable=True),
        sa.Column('parameters', sa.JSON(), server_default='{}'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('resolved_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_approvals_user_status', 'approval_requests', ['user_id', 'status'])

    # Audit Log
    op.create_table('audit_log',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('tenant_id', sa.String(), sa.ForeignKey('tenants.id'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('details', sa.JSON(), server_default='{}'),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_user', 'audit_log', ['user_id'])
    op.create_index('ix_audit_action', 'audit_log', ['action'])

    # Webhooks
    op.create_table('webhooks',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('events', sa.JSON(), server_default='[]'),
        sa.Column('secret', sa.String(255), nullable=True),
        sa.Column('active', sa.Boolean(), server_default='true'),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True),
        sa.Column('failure_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # API Keys (for public API)
    op.create_table('api_keys',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('prefix', sa.String(10), nullable=False),
        sa.Column('scopes', sa.JSON(), server_default='[]'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Notifications
    op.create_table('notifications',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), server_default='{}'),
        sa.Column('read', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_notifications_user', 'notifications', ['user_id', 'read'])

    # Billing / Subscriptions
    op.create_table('subscriptions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('plan', sa.String(20), server_default='free'),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Plugin Registry
    op.create_table('plugins',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('icon_url', sa.String(500), nullable=True),
        sa.Column('manifest', sa.JSON(), server_default='{}'),
        sa.Column('downloads', sa.Integer(), server_default='0'),
        sa.Column('rating', sa.Float(), server_default='0'),
        sa.Column('published', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    tables = [
        'plugins', 'subscriptions', 'notifications', 'api_keys',
        'webhooks', 'audit_log', 'approval_requests', 'standing_orders',
        'projects', 'memories', 'integrations', 'chat_messages',
        'conversations', 'users', 'tenants',
    ]
    for table in tables:
        op.drop_table(table)
    op.execute('DROP EXTENSION IF EXISTS vector')
