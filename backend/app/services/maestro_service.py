from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.cliente_maestro import ClienteMaestro
from app.services.excel_parser import MaestroRow


def merge_maestro(db: Session, rows: list[MaestroRow]) -> dict:
    """
    Merge maestro Excel rows into ClienteMaestro table.

    CRITICAL: Never overwrites prefiere_no_recibir_email=True.
    If a client was marked for baja, the flag stays True even if
    the new Excel doesn't include them or includes them with different data.
    """
    nuevos = 0
    actualizados = 0
    for row in rows:
        existing = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == row.clave_union).first()
        if existing:
            existing.nombre = row.nombre
            existing.localidad = row.localidad
            # CRITICAL BUSINESS RULE: never overwrite prefiere_no_recibir_email if True
            if not existing.prefiere_no_recibir_email:
                existing.email = row.email
            existing.actualizado_en = datetime.now(timezone.utc)
            actualizados += 1
        else:
            db.add(ClienteMaestro(
                clave_union=row.clave_union,
                nombre=row.nombre,
                email=row.email,
                localidad=row.localidad,
                actualizado_en=datetime.now(timezone.utc),
            ))
            nuevos += 1
    db.commit()
    total = db.query(ClienteMaestro).count()
    return {"nuevos": nuevos, "actualizados": actualizados, "total": total}


def crear_cliente_manual(
    db: Session,
    clave_union: str,
    nombre: str,
    email: str | None,
    localidad: str | None,
) -> ClienteMaestro:
    """
    Crea un cliente manualmente en el Maestro. Lanza ValueError con el mensaje
    a mostrar si ya existe un cliente (activo o inactivo) con esa clave_union.
    """
    existing = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == clave_union).first()
    if existing:
        if existing.activo:
            raise ValueError(f"Ya existe un cliente activo con la clave '{clave_union}'.")
        raise ValueError(
            f"Ya existe un cliente con la clave '{clave_union}', pero está inactivo. "
            "Reactivalo en vez de crear uno nuevo."
        )

    cliente = ClienteMaestro(
        clave_union=clave_union,
        nombre=nombre,
        email=(email or "").strip() or None,
        localidad=(localidad or "").strip() or None,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente
