"""envio_saldado_en

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.add_column(sa.Column("saldado_en", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.drop_column("saldado_en")
