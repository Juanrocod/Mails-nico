from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class MinutaSession:
    id: str
    cliente_nombre: str
    cliente_email: str
    cuenta_comitente: str
    cuenta_cotapartista: str
    instrumento: str
    tipo: str
    cantidad: float
    precio: float
    moneda: str
    liquidacion: str
    fecha_operacion: datetime
    dj_aplicada: bool
    dj_texto: Optional[str]
    estado: str
    texto_minuta: str
    texto_editado: bool
    creado_en: datetime


@dataclass
class _SessionData:
    minutas: list[MinutaSession] = field(default_factory=list)


_store: dict[str, _SessionData] = {}


def _get_or_create(user_id: str) -> _SessionData:
    if user_id not in _store:
        _store[user_id] = _SessionData()
    return _store[user_id]


def clear_session(user_id: str) -> None:
    _store.pop(user_id, None)


def clear_borradores(user_id: str) -> None:
    session = _get_or_create(user_id)
    session.minutas = [m for m in session.minutas if m.estado != "BORRADOR"]


def add_minutas(user_id: str, minutas: list[MinutaSession]) -> None:
    _get_or_create(user_id).minutas.extend(minutas)


def get_minutas(user_id: str, estado: str) -> list[MinutaSession]:
    return [m for m in _get_or_create(user_id).minutas if m.estado == estado]


def get_minuta(user_id: str, minuta_id: str) -> Optional[MinutaSession]:
    for m in _get_or_create(user_id).minutas:
        if m.id == minuta_id:
            return m
    return None


def update_minuta_texto(user_id: str, minuta_id: str, texto: str) -> Optional[MinutaSession]:
    m = get_minuta(user_id, minuta_id)
    if m is None:
        return None
    m.texto_minuta = texto
    m.texto_editado = True
    return m


def marcar_enviada(user_id: str, minuta_id: str) -> Optional[MinutaSession]:
    m = get_minuta(user_id, minuta_id)
    if m is None:
        return None
    m.estado = "ENVIADO"
    return m
