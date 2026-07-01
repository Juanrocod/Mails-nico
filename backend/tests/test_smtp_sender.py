import asyncio
from unittest.mock import patch
from decimal import Decimal
from app.services.smtp_sender import enviar_ciclo
from app.models.envio import Envio, EstadoEnvio


def _make_envio_db(db, ciclo, clave, nombre, email, monto):
    from datetime import datetime, timezone
    e = Envio(
        ciclo_id=ciclo.id,
        ciclo_numero=1,
        clave_union=clave,
        nombre_consorcio=nombre,
        email=email,
        monto=Decimal(str(monto)),
        estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.flush()
    return e


def _make_ciclo(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    c = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    return c


def test_enviar_ciclo_actualiza_estado_a_no_contestado(db, plantilla_default):
    ciclo = _make_ciclo(db)
    envio = _make_envio_db(db, ciclo, "C001", "Consorcio", "test@mail.com", 5000)

    progreso = []

    async def on_progress(e):
        progreso.append(e.id)

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<msg-id-123@yahoo.com>"
        asyncio.get_event_loop().run_until_complete(
            enviar_ciclo([envio], db, on_progress, rate_limit_override=(2, 0.01))
        )

    db.refresh(envio)
    assert envio.message_id == "<msg-id-123@yahoo.com>"
    assert envio.estado == EstadoEnvio.NO_CONTESTADO
    assert envio.enviado_en is not None
    assert envio.id in progreso


def test_enviar_ciclo_respeta_rate_limit(db, plantilla_default):
    ciclo = _make_ciclo(db)
    envios = [_make_envio_db(db, ciclo, f"C{i:03d}", f"Cons {i}", f"c{i}@mail.com", 1000) for i in range(4)]

    calls = []

    async def on_progress(e):
        calls.append(e.id)

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<mid@yahoo.com>"
        asyncio.get_event_loop().run_until_complete(
            enviar_ciclo(envios, db, on_progress, rate_limit_override=(2, 0.05))
        )

    assert len(calls) == 4
