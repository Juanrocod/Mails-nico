"""initial

Revision ID: 0001
Revises:
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "plantilla",
        sa.Column("id", sa.Integer(), primary_key=True, default=1),
        sa.Column("asunto", sa.String(255), nullable=False),
        sa.Column("cuerpo_html", sa.Text(), nullable=False),
        sa.Column("nombre_empresa", sa.String(255), nullable=False),
        sa.Column("logo_url", sa.String(512), nullable=True),
        sa.Column("color_primario", sa.String(7), nullable=False),
        sa.Column("monto_minimo", sa.Numeric(12, 2), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "clientes_maestro",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clave_union", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("localidad", sa.String(255), nullable=True),
        sa.Column("prefiere_no_recibir_email", sa.Boolean(), nullable=False, default=False),
        sa.Column("activo", sa.Boolean(), nullable=False, default=True),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "ciclos",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, default=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "envios",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ciclo_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ciclos.id"), nullable=False),
        sa.Column("ciclo_numero", sa.Integer(), nullable=False),
        sa.Column("clave_union", sa.String(100), nullable=False),
        sa.Column("nombre_consorcio", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("estado", sa.Enum("NO_CONTESTADO", "CONTESTADO", "PAGO", "REBOTADO", "SIN_EMAIL", "FILTRADO", name="estadoenvio"), nullable=False),
        sa.Column("motivo_filtrado", sa.Enum("MONTO_MINIMO", "DADO_DE_BAJA", name="motivofiltrado"), nullable=True),
        sa.Column("message_id", sa.String(512), nullable=True),
        sa.Column("reply_snippet", sa.Text(), nullable=True),
        sa.Column("enviado_en", sa.DateTime(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_envios_ciclo_id", "envios", ["ciclo_id"])
    op.create_index("ix_envios_clave_union", "envios", ["clave_union"])
    op.create_index("ix_envios_message_id", "envios", ["message_id"])


def downgrade() -> None:
    op.drop_table("envios")
    op.drop_table("ciclos")
    op.drop_table("clientes_maestro")
    op.drop_table("plantilla")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS estadoenvio")
    op.execute("DROP TYPE IF EXISTS motivofiltrado")
