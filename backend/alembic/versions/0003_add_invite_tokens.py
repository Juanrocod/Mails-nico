"""add invite_tokens table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invite_tokens',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('tipo', sa.String(length=10), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('expira_en', sa.DateTime(), nullable=False),
        sa.Column('usado_en', sa.DateTime(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('ix_invite_tokens_token', 'invite_tokens', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_invite_tokens_token', table_name='invite_tokens')
    op.drop_table('invite_tokens')
