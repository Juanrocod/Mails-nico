"""proveedor_email_configurable

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("configuracion_sistema") as batch_op:
        batch_op.add_column(
            sa.Column("proveedor_activo", sa.String(20), nullable=False, server_default="yahoo")
        )
        batch_op.add_column(sa.Column("gmail_email", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("gmail_app_password_encrypted", sa.String(512), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("configuracion_sistema") as batch_op:
        batch_op.drop_column("gmail_app_password_encrypted")
        batch_op.drop_column("gmail_email")
        batch_op.drop_column("proveedor_activo")
