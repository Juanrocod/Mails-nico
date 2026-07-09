"""Limpieza de la DB de produccion para dejar el sistema listo para el cliente.

DESTRUCTIVO E IRREVERSIBLE. Por defecto NO borra nada: solo muestra que haria
(dry-run). Para ejecutar de verdad hay que pasar --ejecutar.

Conserva SIEMPRE la tabla `users` (el login del operario). El resto se limpia,
salvo que se pidan explicitamente los flags --conservar-*.

Uso:
    # Ver que haria, sin tocar nada (recomendado primero):
    DATABASE_URL=postgresql://... python backend/scripts/limpiar_db_produccion.py

    # Ejecutar de verdad:
    DATABASE_URL=postgresql://... python backend/scripts/limpiar_db_produccion.py --ejecutar

    # Ejecutar pero conservando el maestro de clientes y la plantilla:
    ... --ejecutar --conservar-maestro --conservar-plantilla
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# El script apunta a la DB del env; damos placeholders para que Settings no falle
# si faltan otras vars que no usamos aca.
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ENCRYPTION_KEY", "x" * 44)
os.environ.setdefault("YAHOO_EMAIL", "placeholder@yahoo.com")
os.environ.setdefault("YAHOO_APP_PASSWORD", "placeholder")

from sqlalchemy import text  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402

# (tabla, motivo) en orden seguro de borrado (hijos antes que padres por la FK
# envios.ciclo_id -> ciclos.id).
TABLAS_BORRABLES = [
    ("envios", None),
    ("ciclos", None),
    ("clientes_maestro", "conservar_maestro"),
    ("plantilla", "conservar_plantilla"),
    ("configuracion_sistema", "conservar_config"),
]


def contar(db, tabla: str) -> int:
    return db.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar() or 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpia la DB de produccion (conserva users).")
    parser.add_argument("--ejecutar", action="store_true", help="Borra de verdad (sin esto es dry-run).")
    parser.add_argument("--conservar-maestro", action="store_true", help="No borrar clientes_maestro.")
    parser.add_argument("--conservar-plantilla", action="store_true", help="No borrar plantilla.")
    parser.add_argument("--conservar-config", action="store_true", help="No borrar configuracion_sistema.")
    args = parser.parse_args()

    conservar = {
        "conservar_maestro": args.conservar_maestro,
        "conservar_plantilla": args.conservar_plantilla,
        "conservar_config": args.conservar_config,
    }

    url = str(engine.url)
    print(f"DB destino: {engine.url.render_as_string(hide_password=True)}")
    if engine.dialect.name != "postgresql":
        print("ADVERTENCIA: la DB destino NO es Postgres. ¿Seguro que apunta a produccion?")

    db = SessionLocal()
    try:
        print("\n== Estado actual ==")
        users = contar(db, "users")
        print(f"  users (SE CONSERVAN): {users}")
        a_borrar = []
        for tabla, flag in TABLAS_BORRABLES:
            n = contar(db, tabla)
            if flag and conservar.get(flag):
                print(f"  {tabla}: {n}  -> se conserva (flag)")
            else:
                print(f"  {tabla}: {n}  -> se BORRA")
                a_borrar.append((tabla, n))

        if not args.ejecutar:
            print("\nDRY-RUN: no se toco nada. Volve a correr con --ejecutar para borrar.")
            return 0

        if users == 0:
            print("\nABORTADO: no hay ningun usuario en `users`. Sembra el operario antes de limpiar.")
            return 1

        print("\n== Ejecutando borrado ==")
        for tabla, _n in a_borrar:
            db.execute(text(f"DELETE FROM {tabla}"))
            print(f"  {tabla}: borrado")
        db.commit()

        print("\n== Estado final ==")
        print(f"  users: {contar(db, 'users')}")
        for tabla, _flag in TABLAS_BORRABLES:
            print(f"  {tabla}: {contar(db, tabla)}")
        print("\nListo. DB limpia, usuario operario conservado.")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"\nERROR (se hizo rollback, no se borro nada): {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
