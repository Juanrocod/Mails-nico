import asyncio
import email
import imaplib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.email_providers import PROVIDERS
from app.models.envio import Envio, EstadoEnvio
from app.services import config_service
from app.services.reply_classifier import classify

_logger = logging.getLogger("mails_nico.imap")
_POLL_INTERVAL = 600  # 10 minutos
_SEARCH_WINDOW_DAYS = 30  # cuanto atras se consideran los Envios "activos" para trackear
_IMAP_TIMEOUT_SECONDS = 15  # evita que una conexion colgada trabe el poll entero

# Con >1 worker de gunicorn, el startup corre en CADA worker, asi que sin este
# lock habria N watchers polleando Yahoo en paralelo (doble/triple conexion IMAP
# cada 10 min + clasificacion repetida). Un advisory lock de Postgres deja que
# solo un worker sea el "lider" que pollea; los demas saltan su turno. En SQLite
# (dev/tests) no hay advisory locks: siempre corre (un solo proceso de todos modos).
_WATCHER_LOCK_KEY = 4827193


async def run_forever():
    """
    Loop infinito que realiza polling IMAP cada 10 minutos.
    Se ejecuta como background task al iniciar la aplicación.
    """
    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(None, _poll_como_lider)
        except Exception as exc:
            # %r y el tipo: algunas excepciones (ej. InvalidToken) tienen str() vacio
            _logger.error("IMAP poll error: %s: %r", type(exc).__name__, exc)
        await asyncio.sleep(_POLL_INTERVAL)


def _es_lider_del_watcher(db) -> bool:
    """True si este worker consigue el advisory lock (o si la DB no es Postgres).
    El lock se mantiene mientras viva la sesion `db` y se libera al cerrarla."""
    if db.bind.dialect.name != "postgresql":
        return True
    return bool(db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": _WATCHER_LOCK_KEY}).scalar())


def _poll_como_lider() -> None:
    """Envuelve el poll del loop de background con el lock de lider, para que un
    solo worker pollee. El refresco manual NO pasa por aca: siempre corre a demanda."""
    lock_db = SessionLocal()
    try:
        if not _es_lider_del_watcher(lock_db):
            _logger.debug("Otro worker es el lider del watcher IMAP; salteo este turno")
            return
        _poll_inbox()
    finally:
        lock_db.close()  # libera el advisory lock si lo tenia


def _poll_inbox(mailbox_lookback_days: int = _SEARCH_WINDOW_DAYS):
    """
    Conexión sincrónica a IMAP para buscar respuestas a Envios activos.
    Se ejecuta en executor para no bloquear el event loop.

    `mailbox_lookback_days` acota cuántos días atrás se escanean MENSAJES en
    la bandeja (para que un refresco manual sea rápido); qué Envios se
    consideran "activos" para trackear siempre usa la ventana completa de
    _SEARCH_WINDOW_DAYS, sin importar este parámetro — así una respuesta a
    un Envio viejo pero todavía sin contestar no se pierde en un refresco
    angosto, solo puede tardar hasta el próximo poll automático en detectarse.
    """
    db = SessionLocal()
    try:
        cutoff_envios = datetime.now(timezone.utc) - timedelta(days=_SEARCH_WINDOW_DAYS)
        active_envios = (
            db.query(Envio)
            .filter(
                Envio.message_id.isnot(None),
                Envio.estado == EstadoEnvio.NO_CONTESTADO,
                Envio.enviado_en >= cutoff_envios,
            )
            .all()
        )
        if not active_envios:
            return

        message_id_map = {e.message_id: e for e in active_envios}

        provider = PROVIDERS[config_service.get_active_provider(db)]
        email_addr, app_password = config_service.get_active_credentials(db)
        mail = imaplib.IMAP4_SSL(provider.imap_host, provider.imap_port, timeout=_IMAP_TIMEOUT_SECONDS)
        try:
            mail.login(email_addr, app_password)
            mail.select("INBOX")

            cutoff_mensajes = datetime.now(timezone.utc) - timedelta(days=mailbox_lookback_days)
            since_date = cutoff_mensajes.strftime("%d-%b-%Y")
            _, data = mail.search(None, f'(SINCE "{since_date}")')
            msg_nums = data[0].split()

            for num in msg_nums:
                _, msg_data = mail.fetch(num, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                in_reply_to = msg.get("In-Reply-To", "").strip()
                references = msg.get("References", "").strip().split()

                matched_envio = message_id_map.get(in_reply_to)
                if matched_envio is None:
                    for ref in references:
                        matched_envio = message_id_map.get(ref.strip())
                        if matched_envio:
                            break

                if matched_envio is None:
                    continue

                new_estado, tiene_adjunto = classify(msg)
                snippet = _extract_snippet(msg)
                matched_envio.estado = new_estado
                matched_envio.reply_snippet = snippet
                matched_envio.reply_en = datetime.now(timezone.utc)
                matched_envio.tiene_adjunto = tiene_adjunto
                matched_envio.actualizado_en = datetime.now(timezone.utc)
                db.add(matched_envio)
                _logger.info("Envio %s → %s", matched_envio.id, new_estado)

            db.commit()
        finally:
            try:
                mail.logout()
            except Exception:
                pass
    finally:
        db.close()


def _extract_snippet(msg) -> str:
    """Extrae los primeros 200 caracteres del cuerpo de texto del email."""
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            payload = part.get_payload(decode=True)
            if payload:
                return payload.decode(errors="replace")[:200]
    return ""
