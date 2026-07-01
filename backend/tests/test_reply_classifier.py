import email
from email.message import EmailMessage
from app.services.reply_classifier import classify
from app.models.envio import EstadoEnvio


def _make_msg(from_addr: str, has_attachment: bool = False, body: str = "Texto") -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["Subject"] = "Re: Recordatorio"
    msg.set_content(body)
    if has_attachment:
        msg.add_attachment(b"%PDF-1.4 fake", maintype="application", subtype="pdf", filename="comprobante.pdf")
    return msg


def test_mailer_daemon_es_rebotado():
    msg = _make_msg("mailer-daemon@yahoo.com")
    assert classify(msg) == EstadoEnvio.REBOTADO


def test_postmaster_es_rebotado():
    msg = _make_msg("postmaster@dominio.com")
    assert classify(msg) == EstadoEnvio.REBOTADO


def test_adjunto_pdf_es_pago():
    msg = _make_msg("consorcio@mail.com", has_attachment=True)
    assert classify(msg) == EstadoEnvio.PAGO


def test_adjunto_imagen_es_pago():
    msg = EmailMessage()
    msg["From"] = "consorcio@mail.com"
    msg.set_content("Adjunto comprobante")
    msg.add_attachment(b"fake-png", maintype="image", subtype="png", filename="pago.png")
    assert classify(msg) == EstadoEnvio.PAGO


def test_solo_texto_es_contestado():
    msg = _make_msg("consorcio@mail.com")
    assert classify(msg) == EstadoEnvio.CONTESTADO
