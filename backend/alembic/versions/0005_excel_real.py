"""Adaptación al Excel real: nueva columna config_dj + tabla config_filtros_minutas

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar columna activar_si_requiere_conformidad a config_dj
    with op.batch_alter_table("config_dj") as batch_op:
        batch_op.add_column(
            sa.Column(
                "activar_si_requiere_conformidad",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )

    # Crear tabla config_filtros_minutas
    op.create_table(
        "config_filtros_minutas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reglas", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("logica", sa.String(length=3), nullable=False, server_default="OR"),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("config_filtros_minutas")
    with op.batch_alter_table("config_dj") as batch_op:
        batch_op.drop_column("activar_si_requiere_conformidad")
