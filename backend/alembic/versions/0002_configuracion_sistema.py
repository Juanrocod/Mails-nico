"""configuracion_sistema

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracion_sistema",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("yahoo_email", sa.String(255), nullable=True),
        sa.Column("yahoo_app_password_encrypted", sa.String(512), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("configuracion_sistema")
