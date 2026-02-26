"""add missing performance indexes

Revision ID: 004
Revises: 003
Create Date: 2026-02-26
"""
from typing import Sequence, Union
from alembic import op


revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index for the hot query: list conversations per user ordered by update time
    op.create_index(
        'ix_conversations_user_updated',
        'conversations',
        ['user_id', 'updated_at'],
    )
    # Composite index for memory fetch ordered by creation time
    op.create_index(
        'ix_memories_user_created',
        'memories',
        ['user_id', 'created_at'],
    )
    # Audit log indexes to avoid full-table scans on activity queries
    op.create_index(
        'ix_audit_logs_user_timestamp',
        'audit_logs',
        ['user_id', 'timestamp'],
    )
    op.create_index(
        'ix_audit_logs_action_timestamp',
        'audit_logs',
        ['action', 'timestamp'],
    )


def downgrade() -> None:
    op.drop_index('ix_audit_logs_action_timestamp', 'audit_logs')
    op.drop_index('ix_audit_logs_user_timestamp', 'audit_logs')
    op.drop_index('ix_memories_user_created', 'memories')
    op.drop_index('ix_conversations_user_updated', 'conversations')
