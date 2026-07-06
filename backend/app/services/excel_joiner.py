from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.validators import is_valid_email
from app.models.cliente_maestro import ClienteMaestro
from app.models.ciclo import Ciclo
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
    rachas: dict[str, int] = field(default_factory=dict)


def _ciclos_consecutivos_deudor(db: Session, clave_union: str) -> int:
    last = (
        db.query(Envio)
        .join(Ciclo, Envio.ciclo_id == Ciclo.id)
        .filter(Envio.clave_union == clave_union)
        .order_by(Ciclo.numero.desc())
        .first()
    )
    # PAGO manual o saldado inferido = racha rota: la proxima deuda arranca de cero.
    if last is None or last.estado == EstadoEnvio.PAGO or last.saldado_en is not None:
        return 0
    return last.ciclo_numero


def join_deudores(db: Session, deudores: list[DeudorRow], monto_minimo: Decimal) -> PreviewData:
    para_enviar = []
    sin_email = []
    filtrados = []
    rachas: dict[str, int] = {}

    claves = [d.clave_union for d in deudores]
    clientes = {
        c.clave_union: c
        for c in db.query(ClienteMaestro).filter(ClienteMaestro.clave_union.in_(claves)).all()
    }

    for deudor in deudores:
        if deudor.clave_union not in rachas:
            rachas[deudor.clave_union] = _ciclos_consecutivos_deudor(db, deudor.clave_union) + 1

        cliente = clientes.get(deudor.clave_union)
        if cliente is None:
            sin_email.append(deudor)
            continue
        if cliente.prefiere_no_recibir_email or not cliente.activo:
            filtrados.append((deudor, "DADO_DE_BAJA"))
            continue
        if deudor.monto < monto_minimo:
            filtrados.append((deudor, "MONTO_MINIMO"))
            continue
        if not cliente.email or not is_valid_email(cliente.email):
            sin_email.append(deudor)
            continue
        ciclo_ant = rachas[deudor.clave_union] - 1
        para_enviar.append(EnvioParsed(
            clave_union=deudor.clave_union,
            nombre=cliente.nombre,
            email=cliente.email,
            localidad=deudor.localidad or cliente.localidad,
            monto=deudor.monto,
            ciclo_numero_anterior=ciclo_ant,
        ))

    return PreviewData(para_enviar=para_enviar, sin_email=sin_email, filtrados=filtrados, rachas=rachas)


def _motivo_invalido_para_reenvio(cliente: Optional[ClienteMaestro]) -> Optional[str]:
    if cliente is None:
        return "El cliente ya no existe en el Maestro."
    if cliente.prefiere_no_recibir_email:
        return "El cliente está dado de baja."
    if not cliente.activo:
        return "El cliente está inactivo en el Maestro."
    if not cliente.email or not is_valid_email(cliente.email):
        return "El cliente no tiene un email válido en el Maestro."
    return None


def revalidar_para_reenvio(db: Session, envio: Envio) -> tuple[bool, Optional[str]]:
    """
    Vuelve a validar un Envio contra el Maestro de Clientes antes de reenviarlo.
    Si es valido, actualiza envio.email y envio.nombre_consorcio con los datos
    actuales del Maestro (sin commitear) y devuelve (True, None). Si no es
    valido, no toca el envio y devuelve (False, "<motivo>").
    """
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == envio.clave_union).first()
    motivo = _motivo_invalido_para_reenvio(cliente)
    if motivo:
        return False, motivo

    envio.email = cliente.email
    envio.nombre_consorcio = cliente.nombre
    return True, None


def revalidar_lote_para_reenvio(db: Session, envios: list[Envio]) -> tuple[list[Envio], list[dict]]:
    """
    Version en lote de revalidar_para_reenvio: una sola consulta al Maestro
    para todas las claves en vez de una por Envio, para no bloquear el event
    loop con N consultas secuenciales cuando se reenvian muchos fallidos.
    """
    claves = [e.clave_union for e in envios]
    clientes = {
        c.clave_union: c
        for c in db.query(ClienteMaestro).filter(ClienteMaestro.clave_union.in_(claves)).all()
    }

    listos: list[Envio] = []
    saltados: list[dict] = []
    for envio in envios:
        cliente = clientes.get(envio.clave_union)
        motivo = _motivo_invalido_para_reenvio(cliente)
        if motivo:
            saltados.append({"id": str(envio.id), "motivo": motivo})
            continue
        envio.email = cliente.email
        envio.nombre_consorcio = cliente.nombre
        listos.append(envio)

    return listos, saltados
