from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.services import imap_watcher, config_service
from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio


def _make_ciclo(db):
    c = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    return c


def _make_envio_no_contestado(db, ciclo, clave, message_id):
    e = Envio(
        ciclo_id=ciclo.id,
        ciclo_numero=1,
        clave_union=clave,
        nombre_consorcio="Consorcio",
        email="test@mail.com",
        monto=Decimal("1000"),
        estado=EstadoEnvio.NO_CONTESTADO,
        message_id=message_id,
        enviado_en=datetime.now(timezone.utc),
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.commit()
    return e


def _usar_sesion_de_test(db, monkeypatch):
    # _poll_inbox abre su propia sesion via SessionLocal(); la reemplazamos por la
    # sesion de test para que vea los datos sembrados por los fixtures, y anulamos
    # close() para no cortar la sesion que el fixture `db` todavia necesita.
    monkeypatch.setattr(imap_watcher, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)


def test_poll_inbox_sin_envios_activos_no_conecta(db, monkeypatch):
    _usar_sesion_de_test(db, monkeypatch)
    with patch("app.services.imap_watcher.imaplib.IMAP4_SSL") as mock_imap:
        imap_watcher._poll_inbox()
    mock_imap.assert_not_called()


def test_poll_inbox_usa_host_yahoo_por_default(db, monkeypatch):
    _usar_sesion_de_test(db, monkeypatch)
    ciclo = _make_ciclo(db)
    _make_envio_no_contestado(db, ciclo, "C001", "<abc@yahoo.com>")

    with patch("app.services.imap_watcher.imaplib.IMAP4_SSL") as mock_imap:
        mock_conn = MagicMock()
        mock_conn.search.return_value = ("OK", [b""])
        mock_imap.return_value = mock_conn
        imap_watcher._poll_inbox()

    mock_imap.assert_called_once_with("imap.mail.yahoo.com", 993)


def test_poll_inbox_usa_host_gmail_cuando_esta_activo(db, monkeypatch):
    _usar_sesion_de_test(db, monkeypatch)
    config_service.save_active_provider(db, "gmail")
    ciclo = _make_ciclo(db)
    _make_envio_no_contestado(db, ciclo, "C002", "<def@gmail.com>")

    with patch("app.services.imap_watcher.imaplib.IMAP4_SSL") as mock_imap:
        mock_conn = MagicMock()
        mock_conn.search.return_value = ("OK", [b""])
        mock_imap.return_value = mock_conn
        imap_watcher._poll_inbox()

    mock_imap.assert_called_once_with("imap.gmail.com", 993)
