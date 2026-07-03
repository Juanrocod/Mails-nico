from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.validators import is_valid_email
from app.models.cliente_maestro import ClienteMaestro
from app.models.envio import Envio, EstadoEnvio
from app.services.excel_parser import DeudorRow


@dataclass
class EnvioParsed:
    clave_union: str
    nombre: str
    email: str
    localidad: Optional[str]
    monto: Decimal
    ciclo_numero_anterior: int


@dataclass
class PreviewData:
    para_enviar: list[EnvioParsed]
    sin_email: list[DeudorRow]
    filtrados: list[tuple[DeudorRow, str]]  # (row, motivo)


def _ciclos_consecutivos_deudor(db: Session, clave_union: str) -> int:
    last = (
        db.query(Envio)
        .filter(Envio.clave_union == clave_union)
        .order_by(Envio.ciclo_numero.desc())
        .first()
    )
    if last is None or last.estado == EstadoEnvio.PAGO:
        return 0
    return last.ciclo_numero


def join_deudores(db: Session, deudores: list[DeudorRow], monto_minimo: Decimal) -> PreviewData:
    para_enviar = []
    sin_email = []
    filtrados = []

    claves = [d.clave_union for d in deudores]
    clientes = {
        c.clave_union: c
        for c in db.query(ClienteMaestro).filter(ClienteMaestro.clave_union.in_(claves)).all()
    }

    for deudor in deudores:
        cliente = clientes.get(deudor.clave_union)
        if cliente is None:
            sin_email.append(deudor)
            continue
        if cliente.prefiere_no_recibir_email:
            filtrados.append((deudor, "DADO_DE_BAJA"))
            continue
        if deudor.monto < monto_minimo:
            filtrados.append((deudor, "MONTO_MINIMO"))
            continue
        if not cliente.email or not is_valid_email(cliente.email):
            sin_email.append(deudor)
            continue
        ciclo_ant = _ciclos_consecutivos_deudor(db, deudor.clave_union)
        para_enviar.append(EnvioParsed(
            clave_union=deudor.clave_union,
            nombre=cliente.nombre,
            email=cliente.email,
            localidad=deudor.localidad or cliente.localidad,
            monto=deudor.monto,
            ciclo_numero_anterior=ciclo_ant,
        ))

    return PreviewData(para_enviar=para_enviar, sin_email=sin_email, filtrados=filtrados)
