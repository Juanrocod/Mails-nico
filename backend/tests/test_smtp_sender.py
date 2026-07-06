import asyncio
import pytest
from unittest.mock import patch, AsyncMock
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


def _cleanup(db, ciclo):
    from app.models.ciclo import Ciclo
    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


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

    _cleanup(db, ciclo)


def test_enviar_ciclo_respeta_rate_limit(db, plantilla_default):
    ciclo = _make_ciclo(db)
    envios = [_make_envio_db(db, ciclo, f"C{i:03d}", f"Cons {i}", f"c{i}@mail.com", 1000) for i in range(4)]

    calls = []

    async def on_progress(e):
        calls.append(e.id)

    with patch("app.services.smtp_sender._send_single_email") as mock_send, \
         patch("app.services.smtp_sender.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_send.return_value = "<mid@yahoo.com>"
        asyncio.get_event_loop().run_until_complete(
            enviar_ciclo(envios, db, on_progress, rate_limit_override=(2, 0.05))
        )

    assert len(calls) == 4
    mock_sleep.assert_called_once()

    _cleanup(db, ciclo)


def test_enviar_ciclo_usa_host_yahoo_por_default(db, plantilla_default):
    ciclo = _make_ciclo(db)
    envio = _make_envio_db(db, ciclo, "C010", "Consorcio", "test@mail.com", 5000)

    async def on_progress(e):
        pass

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<msg-id@yahoo.com>"
        asyncio.get_event_loop().run_until_complete(
            enviar_ciclo([envio], db, on_progress, rate_limit_override=(2, 0.01))
        )

    args = mock_send.call_args.args
    assert args[3] == "smtp.mail.yahoo.com"
    assert args[4] == 587
    db.refresh(envio)
    assert envio.proveedor == "yahoo"

    _cleanup(db, ciclo)


def test_enviar_ciclo_usa_host_gmail_cuando_esta_activo(db, plantilla_default):
    from app.services import config_service
    config_service.save_active_provider(db, "gmail")

    ciclo = _make_ciclo(db)
    envio = _make_envio_db(db, ciclo, "C011", "Consorcio2", "test2@mail.com", 3000)

    async def on_progress(e):
        pass

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<msg-id@gmail.com>"
        asyncio.get_event_loop().run_until_complete(
            enviar_ciclo([envio], db, on_progress, rate_limit_override=(2, 0.01))
        )

    args = mock_send.call_args.args
    assert args[3] == "smtp.gmail.com"
    assert args[4] == 587
    db.refresh(envio)
    assert envio.proveedor == "gmail"

    _cleanup(db, ciclo)


def test_enviar_ciclo_propaga_error_si_falla_config(db, plantilla_default):
    """Si falla la carga de plantilla/proveedor/credenciales, enviar_ciclo debe
    levantar (no tragarse el error en silencio) para que el caller pueda
    avisarle al operario en vez de reportar 0 envios como si nada."""
    ciclo = _make_ciclo(db)
    envio = _make_envio_db(db, ciclo, "C020", "Consorcio", "test@mail.com", 5000)

    async def on_progress(e):
        pass

    with patch("app.services.smtp_sender.db_config.load_plantilla", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            asyncio.get_event_loop().run_until_complete(
                enviar_ciclo([envio], db, on_progress, rate_limit_override=(2, 0.01))
            )

    db.refresh(envio)
    assert envio.message_id is None


def test_enviar_ciclo_comparte_rate_limit_entre_invocaciones(db, plantilla_default):
    """El rate limit tiene que ser compartido a nivel de proceso: dos llamadas
    separadas a enviar_ciclo (ej. dos clicks de "Reenviar") deben sumar al
    mismo contador en vez de arrancar cada una desde cero."""
    ciclo = _make_ciclo(db)
    envio_a = _make_envio_db(db, ciclo, "C021", "Cons A", "a@mail.com", 1000)
    envio_b = _make_envio_db(db, ciclo, "C022", "Cons B", "b@mail.com", 1000)
    envio_c = _make_envio_db(db, ciclo, "C023", "Cons C", "c@mail.com", 1000)

    async def on_progress(e):
        pass

    with patch("app.services.smtp_sender._send_single_email") as mock_send, \
         patch("app.services.smtp_sender.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_send.return_value = "<mid@yahoo.com>"
        loop = asyncio.get_event_loop()
        # batch_size=2: la primera llamada consume 2 lugares, la segunda (un solo
        # envio) deberia disparar la espera al toparse con el mismo limite.
        loop.run_until_complete(
            enviar_ciclo([envio_a, envio_b], db, on_progress, rate_limit_override=(2, 0.05))
        )
        loop.run_until_complete(
            enviar_ciclo([envio_c], db, on_progress, rate_limit_override=(2, 0.05))
        )

    mock_sleep.assert_called_once()

    _cleanup(db, ciclo)
