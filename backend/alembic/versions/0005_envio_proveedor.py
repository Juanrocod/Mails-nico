"""envio_proveedor

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.add_column(sa.Column("proveedor", sa.String(20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.drop_column("proveedor")
