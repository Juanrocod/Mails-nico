import asyncio
import email
import imaplib
import logging
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.core.email_providers import PROVIDERS
from app.models.envio import Envio, EstadoEnvio
from app.services import config_service
from app.services.reply_classifier import classify

_logger = logging.getLogger("mails_nico.imap")
_POLL_INTERVAL = 600  # 10 minutos
_SEARCH_WINDOW_DAYS = 30


async def run_forever():
    """
    Loop infinito que realiza polling IMAP cada 10 minutos.
    Se ejecuta como background task al iniciar la aplicación.
    """
    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(None, _poll_inbox)
        except Exception as exc:
            _logger.error("IMAP poll error: %s", exc)
        await asyncio.sleep(_POLL_INTERVAL)


def _poll_inbox():
    """
    Conexión sincrónica a IMAP para buscar respuestas a Envios activos.
    Se ejecuta en executor para no bloquear el event loop.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=_SEARCH_WINDOW_DAYS)
        active_envios = (
            db.query(Envio)
            .filter(
                Envio.message_id.isnot(None),
                Envio.estado == EstadoEnvio.NO_CONTESTADO,
                Envio.enviado_en >= cutoff,
            )
            .all()
        )
        if not active_envios:
            return

        message_id_map = {e.message_id: e for e in active_envios}

        provider = PROVIDERS[config_service.get_active_provider(db)]
        email_addr, app_password = config_service.get_active_credentials(db)
        mail = imaplib.IMAP4_SSL(provider.imap_host, provider.imap_port)
        try:
            mail.login(email_addr, app_password)
            mail.select("INBOX")

            since_date = cutoff.strftime("%d-%b-%Y")
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
