import asyncio
import logging
import smtplib
import ssl
import time
import traceback
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Awaitable, Callable, Deque, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email_providers import PROVIDERS
from app.services import config_service
from app.models.envio import Envio
from app.services import db_config
from app.services.email_generator import generate_email
from app.services.excel_joiner import EnvioParsed

_logger = logging.getLogger("mails_nico.smtp")

_DEFAULT_RATE_LIMIT: Tuple[int, float] = (5, 30.0)  # 5 mails, luego esperar 30 segundos
_SMTP_TIMEOUT_SECONDS = 15  # evita que una conexion/login colgado trabe todo el ciclo

# Estado a nivel de proceso (no por-invocacion): comparte el rate limit entre
# el envio masivo y los reenvios individuales, para que clicks sucesivos de
# "Reenviar" no lo salteen enviando cada uno con su propio contador en cero.
_send_timestamps: "Deque[float]" = deque()
_rate_limit_lock = asyncio.Lock()


async def _esperar_turno_rate_limit(batch_size: int, window_seconds: float) -> None:
    async with _rate_limit_lock:
        now = time.monotonic()
        while _send_timestamps and now - _send_timestamps[0] >= window_seconds:
            _send_timestamps.popleft()
        if len(_send_timestamps) >= batch_size:
            _logger.info("Rate limit: esperando %.1f segundos", window_seconds)
            await asyncio.sleep(window_seconds)
            _send_timestamps.clear()
        _send_timestamps.append(time.monotonic())


def _send_single_email(msg, from_email: str, app_password: str, smtp_host: str, smtp_port: int) -> str:
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=_SMTP_TIMEOUT_SECONDS) as server:
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
    try:
        plantilla = db_config.load_plantilla(db)
        batch_size, batch_wait = rate_limit_override or _DEFAULT_RATE_LIMIT
        provider = PROVIDERS[config_service.get_active_provider(db)]
        from_email, app_password = config_service.get_active_credentials(db)
    except Exception as exc:
        _logger.error(
            "No se pudo preparar el envio (plantilla/proveedor/credenciales)\n%s", traceback.format_exc()
        )
        raise RuntimeError(
            "No se pudo enviar: revisá la plantilla y las credenciales del proveedor de email en Configuración."
        ) from exc

    loop = asyncio.get_running_loop()

    for envio in envios:
        await _esperar_turno_rate_limit(batch_size, batch_wait)

        try:
            parsed = EnvioParsed(
                clave_union=envio.clave_union,
                nombre=envio.nombre_consorcio,
                email=envio.email,
                localidad=None,
                monto=envio.monto,
                ciclo_numero_anterior=envio.ciclo_numero - 1,
            )
            msg = generate_email(parsed, plantilla, unsubscribe_base_url=settings.BACKEND_PUBLIC_URL)
            msg["From"] = from_email
            msg_id = f"<{uuid.uuid4().hex}@{provider.message_id_domain}>"
            msg["Message-ID"] = msg_id

            returned_id = await loop.run_in_executor(
                None,
                _send_single_email,
                msg,
                from_email,
                app_password,
                provider.smtp_host,
                provider.smtp_port,
            )
            envio.message_id = returned_id or msg_id
            envio.enviado_en = datetime.now(timezone.utc)
            db.add(envio)
            db.commit()
            await on_progress(envio)
            _logger.info("Enviado a %s (message_id=%s)", envio.email, envio.message_id)
        except Exception:
            _logger.error("Error enviando a %s\n%s", envio.email, traceback.format_exc())
