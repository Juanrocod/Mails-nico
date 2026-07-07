from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio


@dataclass
class EnvioResumen:
    monto: Decimal
    saldado: bool
    con_mail: bool


@dataclass
class ResumenData:
    hay_ciclo_activo: bool
    deuda_total: Decimal
    deuda_total_anterior: Optional[Decimal]
    deudores: int
    deudores_anterior: Optional[int]
    cobrado: Optional[Decimal]
    efectividad: Optional[float]


@dataclass
class EvolucionItem:
    numero: int
    fecha: datetime
    deuda_total: Decimal
    deudores: int
    cobrado: Optional[Decimal]


def _envios_por_clave(db: Session, ciclo_id) -> dict[str, EnvioResumen]:
    rows = (
        db.query(Envio.clave_union, Envio.monto, Envio.saldado_en, Envio.message_id)
        .filter(Envio.ciclo_id == ciclo_id)
        .all()
    )
    return {
        clave: EnvioResumen(monto=monto, saldado=saldado_en is not None, con_mail=message_id is not None)
        for clave, monto, saldado_en, message_id in rows
    }


def _cobrado_entre(anteriores: dict[str, EnvioResumen], actuales: dict[str, EnvioResumen]) -> Decimal:
    """Deuda eliminada entre dos ciclos: montos saldados completos + reducciones
    de monto de los que repiten (pagos parciales). Los aumentos no restan."""
    cobrado = Decimal("0")
    for clave, ant in anteriores.items():
        if ant.saldado:
            cobrado += ant.monto
        elif clave in actuales:
            reduccion = ant.monto - actuales[clave].monto
            if reduccion > 0:
                cobrado += reduccion
    return cobrado


def _efectividad(anteriores: dict[str, EnvioResumen]) -> Optional[float]:
    con_mail = [e for e in anteriores.values() if e.con_mail]
    if not con_mail:
        return None
    saldaron = sum(1 for e in con_mail if e.saldado)
    return round(100 * saldaron / len(con_mail), 1)


def resumen(db: Session) -> ResumenData:
    activo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if activo is None:
        return ResumenData(
            hay_ciclo_activo=False, deuda_total=Decimal("0"), deuda_total_anterior=None,
            deudores=0, deudores_anterior=None, cobrado=None, efectividad=None,
        )
    anterior = (
        db.query(Ciclo)
        .filter(Ciclo.numero < activo.numero)
        .order_by(Ciclo.numero.desc())
        .first()
    )
    envios_activo = _envios_por_clave(db, activo.id)
    deuda_total = sum((e.monto for e in envios_activo.values()), start=Decimal("0"))

    if anterior is None:
        return ResumenData(
            hay_ciclo_activo=True, deuda_total=deuda_total, deuda_total_anterior=None,
            deudores=len(envios_activo), deudores_anterior=None, cobrado=None, efectividad=None,
        )

    envios_anterior = _envios_por_clave(db, anterior.id)
    return ResumenData(
        hay_ciclo_activo=True,
        deuda_total=deuda_total,
        deuda_total_anterior=sum((e.monto for e in envios_anterior.values()), start=Decimal("0")),
        deudores=len(envios_activo),
        deudores_anterior=len(envios_anterior),
        cobrado=_cobrado_entre(envios_anterior, envios_activo),
        efectividad=_efectividad(envios_anterior),
    )


def evolucion(db: Session) -> list[EvolucionItem]:
    ciclos = db.query(Ciclo).order_by(Ciclo.numero).all()
    items: list[EvolucionItem] = []
    envios_previos: Optional[dict[str, EnvioResumen]] = None
    for ciclo in ciclos:
        envios = _envios_por_clave(db, ciclo.id)
        items.append(EvolucionItem(
            numero=ciclo.numero,
            fecha=ciclo.creado_en,
            deuda_total=sum((e.monto for e in envios.values()), start=Decimal("0")),
            deudores=len(envios),
            cobrado=_cobrado_entre(envios_previos, envios) if envios_previos is not None else None,
        ))
        envios_previos = envios
    return items


_UMBRAL_VENCIDA_DIAS = 90


def _a_naive_utc(dt: datetime) -> datetime:
    """Normaliza a naive-UTC. Ciclo.creado_en vuelve naive desde Postgres pero
    puede ser aware en la sesion de test; asi las comparaciones nunca mezclan."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def deudor_desde_por_clave(db: Session, claves: set[str]) -> dict[str, datetime]:
    """Para cada clave con deuda vigente, la fecha del primer ciclo de su racha
    actual ('deudor desde'). Claves sin deuda vigente (envio mas reciente PAGO o
    saldado) no aparecen. Una sola query cross-ciclo."""
    if not claves:
        return {}
    rows = (
        db.query(Envio.clave_union, Ciclo.creado_en, Envio.estado, Envio.saldado_en)
        .join(Ciclo, Envio.ciclo_id == Ciclo.id)
        .filter(Envio.clave_union.in_(claves))
        .order_by(Ciclo.numero.desc())
        .all()
    )
    por_clave: dict[str, list] = {}
    for clave, creado_en, estado, saldado_en in rows:
        por_clave.setdefault(clave, []).append((creado_en, estado, saldado_en))

    resultado: dict[str, datetime] = {}
    for clave, envios in por_clave.items():
        streak_start = None
        for creado_en, estado, saldado_en in envios:  # mas reciente primero
            if estado == EstadoEnvio.PAGO or saldado_en is not None:
                break  # cierra una racha anterior; no es parte de la vigente
            streak_start = creado_en
        if streak_start is not None:
            resultado[clave] = streak_start
    return resultado
