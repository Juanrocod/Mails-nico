"""security hardening post-audit

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def upgrade() -> None:
    # 1. Fix invite_tokens: DateTime → DateTime(timezone=True)
    # postgresql_using convierte los valores existentes de naive a UTC-aware en PostgreSQL.
    # batch_alter_table is required for SQLite compatibility.
    with op.batch_alter_table("invite_tokens") as batch_op:
        for col, nullable in [('expira_en', False), ('usado_en', True), ('creado_en', False)]:
            batch_op.alter_column(
                col,
                type_=sa.DateTime(timezone=True),
                existing_type=sa.DateTime(),
                existing_nullable=nullable,
                postgresql_using=f"{col} AT TIME ZONE 'UTC'",
            )

    # 2. Drop índice duplicado en invite_tokens.token
    # La migración 0003 creó tanto UniqueConstraint('token') (→ invite_tokens_token_key)
    # como op.create_index('ix_invite_tokens_token', ..., unique=True) — dos índices físicos.
    op.drop_index('ix_invite_tokens_token', table_name='invite_tokens')

    # 3. Drop tablas Fase 2 (violan ADR-0006: master no tiene persistencia de órdenes)
    # Orden respeta foreign keys: audit_events → ordenes → excel_uploads
    if not _is_sqlite():
        op.drop_index('ix_audit_events_orden_id', table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_table('ordenes')
    op.drop_table('excel_uploads')
    op.drop_table('dj_templates')

    # 4. Drop enum types creados junto con las tablas Fase 2 (PostgreSQL only)
    if not _is_sqlite():
        op.execute('DROP TYPE IF EXISTS accionaudit')
        op.execute('DROP TYPE IF EXISTS estadominuta')
        op.execute('DROP TYPE IF EXISTS condicionliquidacion')
        op.execute('DROP TYPE IF EXISTS tipoperacion')


def downgrade() -> None:
    # Recrear enum types primero (requeridos por las columnas de las tablas) — PostgreSQL only
    if not _is_sqlite():
        op.execute("CREATE TYPE tipoperacion AS ENUM ('COMPRA', 'VENTA')")
        op.execute("CREATE TYPE condicionliquidacion AS ENUM ('CI', '24HS', '48HS')")
        op.execute(
            "CREATE TYPE estadominuta AS ENUM "
            "('BORRADOR', 'APROBADO', 'ENVIADO', 'CONFIRMADO', 'ALERTA')"
        )
        op.execute(
            "CREATE TYPE accionaudit AS ENUM "
            "('CREADA', 'EDITADA', 'APROBADA', 'ENVIADA', 'CONFIRMADA', 'ALERTA_GENERADA')"
        )

    # Recrear tablas Fase 2 vacías
    op.create_table(
        'dj_templates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('reglas', sa.Text(), nullable=False),
        sa.Column('prioridad', sa.Integer(), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre'),
    )
    op.create_table(
        'excel_uploads',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('usuario_id', sa.String(36), nullable=False),
        sa.Column('nombre_archivo', sa.String(length=255), nullable=False),
        sa.Column('total_ordenes', sa.Integer(), nullable=False),
        sa.Column('ordenes_validas', sa.Integer(), nullable=False),
        sa.Column('ordenes_con_error', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'ordenes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('excel_upload_id', sa.String(36), nullable=False),
        sa.Column('cliente_nombre', sa.String(length=255), nullable=False),
        sa.Column('cliente_email', sa.String(length=512), nullable=False),
        sa.Column('cuenta_comitente', sa.String(length=256), nullable=False),
        sa.Column('cuenta_cotapartista', sa.String(length=256), nullable=False),
        sa.Column('instrumento', sa.String(length=100), nullable=False),
        sa.Column('tipo', sa.String(length=10), nullable=False),
        sa.Column('cantidad', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('precio', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('moneda', sa.String(length=10), nullable=False),
        sa.Column('liquidacion', sa.String(length=10), nullable=False),
        sa.Column('fecha_operacion', sa.DateTime(), nullable=False),
        sa.Column('dj_aplicada', sa.Boolean(), nullable=False),
        sa.Column('dj_tipo', sa.String(length=100), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('texto_minuta', sa.Text(), nullable=False),
        sa.Column('texto_editado', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['excel_upload_id'], ['excel_uploads.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('orden_id', sa.String(36), nullable=False),
        sa.Column('usuario_id', sa.String(36), nullable=True),
        sa.Column('accion', sa.String(length=30), nullable=False),
        sa.Column('ip_origen', sa.String(length=45), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('detalle', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['orden_id'], ['ordenes.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_events_orden_id', 'audit_events', ['orden_id'], unique=False)

    # Restaurar índice duplicado en invite_tokens.token (para que downgrade sea simétrico)
    op.create_index('ix_invite_tokens_token', 'invite_tokens', ['token'], unique=True)

    # Revertir invite_tokens a DateTime sin timezone
    with op.batch_alter_table("invite_tokens") as batch_op:
        for col, nullable in [('expira_en', False), ('usado_en', True), ('creado_en', False)]:
            batch_op.alter_column(
                col,
                type_=sa.DateTime(),
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=nullable,
            )
