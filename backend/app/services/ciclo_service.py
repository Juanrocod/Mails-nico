from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.envio import Envio


def marcar_saldados(db: Session, ciclo_anterior_id, claves_nuevas: set[str]) -> int:
    """
    Inferencia de pago por ausencia: todo Envio del ciclo anterior cuya clave
    no figura entre los deudores del Excel nuevo se marca saldado_en=now.
    Aplica a todos los estados (el Excel de deudores es la fuente de verdad de
    quien debe). No commitea — el caller decide cuando.
    Devuelve la cantidad de envios marcados.
    """
    envios_anteriores = (
        db.query(Envio)
        .filter(Envio.ciclo_id == ciclo_anterior_id, Envio.saldado_en.is_(None))
        .all()
    )
    ahora = datetime.now(timezone.utc)
    count = 0
    for envio in envios_anteriores:
        if envio.clave_union not in claves_nuevas:
            envio.saldado_en = ahora
            db.add(envio)
            count += 1
    return count
