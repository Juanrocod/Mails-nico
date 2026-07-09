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


def _cleanup(db, ciclo):
    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_es_lider_en_sqlite_siempre_true(db):
    # En SQLite (dev/tests) no hay advisory locks: el watcher siempre corre.
    assert imap_watcher._es_lider_del_watcher(db) is True


def test_poll_como_lider_pollea_cuando_es_lider(db, monkeypatch):
    _usar_sesion_de_test(db, monkeypatch)
    monkeypatch.setattr(imap_watcher, "_es_lider_del_watcher", lambda _db: True)
    with patch("app.services.imap_watcher._poll_inbox") as mock_poll:
        imap_watcher._poll_como_lider()
    mock_poll.assert_called_once()


def test_poll_como_lider_saltea_cuando_no_es_lider(db, monkeypatch):
    _usar_sesion_de_test(db, monkeypatch)
    monkeypatch.setattr(imap_watcher, "_es_lider_del_watcher", lambda _db: False)
    with patch("app.services.imap_watcher._poll_inbox") as mock_poll:
        imap_watcher._poll_como_lider()
    mock_poll.assert_not_called()


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

    mock_imap.assert_called_once_with("imap.mail.yahoo.com", 993, timeout=imap_watcher._IMAP_TIMEOUT_SECONDS)

    _cleanup(db, ciclo)


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

    mock_imap.assert_called_once_with("imap.gmail.com", 993, timeout=imap_watcher._IMAP_TIMEOUT_SECONDS)

    _cleanup(db, ciclo)


def test_poll_inbox_mailbox_lookback_days_acota_el_since_pero_no_los_envios_activos(db, monkeypatch):
    """El refresco manual pasa mailbox_lookback_days chico para que el SINCE
    de IMAP sea angosto (rapido), pero un Envio viejo sin contestar sigue
    entrando en active_envios igual (sino su respuesta nunca se buscaria)."""
    from datetime import timedelta

    _usar_sesion_de_test(db, monkeypatch)
    ciclo = _make_ciclo(db)
    envio_viejo = _make_envio_no_contestado(db, ciclo, "C003", "<viejo@yahoo.com>")
    envio_viejo.enviado_en = datetime.now(timezone.utc) - timedelta(days=20)
    db.commit()

    with patch("app.services.imap_watcher.imaplib.IMAP4_SSL") as mock_imap:
        mock_conn = MagicMock()
        mock_conn.search.return_value = ("OK", [b""])
        mock_imap.return_value = mock_conn
        imap_watcher._poll_inbox(mailbox_lookback_days=1)

    # Se conecto igual (el envio viejo sigue contando como "activo" para
    # decidir si vale la pena conectarse), pero el SINCE usado es de ~1 dia
    # atras, no de los 30 dias completos.
    mock_imap.assert_called_once()
    since_arg = mock_conn.search.call_args.args[1]
    fecha_ayer = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%d-%b-%Y")
    assert fecha_ayer in since_arg

    _cleanup(db, ciclo)
