---
paths:
  - "backend/alembic/**"
  - "backend/app/models/**/*.py"
---

## Base de datos

- **SQLite** en dev (`dev.db`), **PostgreSQL** (Neon) en producción
- El código debe correr en ambos: no usar features exclusivos de Postgres sin fallback
  (ej. `pg_try_advisory_lock` en `imap_watcher` se guardea por `dialect.name == "postgresql"`)

## Migraciones Alembic

- Cadena actual: `0001_initial` → `0002_configuracion_sistema` → `0003_envio_reply_fields`
  → `0004_proveedor_email` → `0005_envio_proveedor` → `0006_envio_saldado_en`
- El entrypoint de prod (`entrypoint.sh`) corre `alembic upgrade head` en cada deploy
- Local: `alembic upgrade head` después de `pip install`

```python
# Usar batch_alter_table SIEMPRE (compatibilidad SQLite/PostgreSQL)
def upgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.add_column(sa.Column("saldado_en", sa.DateTime(), nullable=True))
```

## Tablas

`users`, `clientes_maestro`, `plantilla` (singleton id=1), `ciclos`, `envios`,
`configuracion_sistema` (singleton id=1). FK: `envios.ciclo_id → ciclos.id`.

## Limpieza de datos

- `scripts/limpiar_db_produccion.py` — dry-run por defecto; `--ejecutar` para borrar.
  Preserva `users`; flags `--conservar-{maestro,plantilla,config}`. Orden FK-seguro:
  `envios` → `ciclos` → resto.
