"""envio reply_en y tiene_adjunto

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.add_column(sa.Column("reply_en", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("tiene_adjunto", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.drop_column("tiene_adjunto")
        batch_op.drop_column("reply_en")
