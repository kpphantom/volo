"""add user_id to chat_messages

Revision ID: 003
Revises: 002
Create Date: 2026-02-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'chat_messages',
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_chat_messages_user_id', 'chat_messages')
    op.drop_column('chat_messages', 'user_id')
