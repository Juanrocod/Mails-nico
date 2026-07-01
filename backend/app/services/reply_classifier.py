import email.message
from app.models.envio import EstadoEnvio


def classify(msg: email.message.Message) -> EstadoEnvio:
    """
    Clasifica una respuesta de email en estados de envío.

    Lógica:
    1. Si From contiene 'mailer-daemon' o 'postmaster' → REBOTADO
    2. Si tiene adjunto (image/* o application/pdf) → PAGO
    3. Si solo texto → CONTESTADO
    """
    from_addr = str(msg.get("From", "")).lower()
    if "mailer-daemon" in from_addr or "postmaster" in from_addr:
        return EstadoEnvio.REBOTADO

    for part in msg.walk():
        ct = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" in disposition or ct.startswith("image/") or ct == "application/pdf":
            return EstadoEnvio.PAGO

    return EstadoEnvio.CONTESTADO
