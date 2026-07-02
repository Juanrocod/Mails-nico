import asyncio
import logging
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, Tuple

from sqlalchemy.orm import Session

from app.services import config_service
from app.models.envio import Envio
from app.services import db_config
from app.services.email_generator import generate_email
from app.services.excel_joiner import EnvioParsed

_logger = logging.getLogger("mails_nico.smtp")

_DEFAULT_RATE_LIMIT: Tuple[int, float] = (5, 30.0)  # 5 mails, luego esperar 30 segundos


def _send_single_email(msg, from_email: str, app_password: str) -> str:
    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.mail.yahoo.com", 587) as server:
        server.starttls(context=context)
        server.login(from_email, app_password)
        server.send_message(msg)
        return msg.get("Message-ID", "")


async def enviar_ciclo(
    envios: list[Envio],
    db: Session,
    on_progress: Callable[[Envio], Awaitable[None]],
    rate_limit_override: Optional[Tuple[int, float]] = None,
) -> None:
    plantilla = db_config.load_plantilla(db)
    batch_size, batch_wait = rate_limit_override or _DEFAULT_RATE_LIMIT
    from_email, app_password = config_service.get_yahoo_credentials(db)

    sent_in_batch = 0
    loop = asyncio.get_running_loop()

    for envio in envios:
        if sent_in_batch >= batch_size:
            _logger.info("Rate limit: esperando %.1f segundos", batch_wait)
            await asyncio.sleep(batch_wait)
            sent_in_batch = 0

        parsed = EnvioParsed(
            clave_union=envio.clave_union,
            nombre=envio.nombre_consorcio,
            email=envio.email,
            localidad=None,
            monto=envio.monto,
            ciclo_numero_anterior=envio.ciclo_numero - 1,
        )
        msg = generate_email(parsed, plantilla)
        msg["From"] = from_email
        msg_id = f"<{uuid.uuid4().hex}@yahoo.com>"
        msg["Message-ID"] = msg_id

        try:
            returned_id = await loop.run_in_executor(
                None, _send_single_email, msg, from_email, app_password
            )
            envio.message_id = returned_id or msg_id
            envio.enviado_en = datetime.now(timezone.utc)
            db.add(envio)
            db.commit()
            sent_in_batch += 1
            await on_progress(envio)
            _logger.info("Enviado a %s (message_id=%s)", envio.email, envio.message_id)
        except Exception as exc:
            _logger.error("Error enviando a %s: %s", envio.email, exc)
