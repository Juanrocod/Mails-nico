from email.message import EmailMessage
from app.models.envio import EstadoEnvio
from app.services.reply_classifier import classify


def test_classify_mailer_daemon_es_rebotado():
    msg = EmailMessage()
    msg["From"] = "MAILER-DAEMON@yahoo.com"
    msg.set_content("Delivery failed")
    assert classify(msg) == (EstadoEnvio.REBOTADO, False)


def test_classify_postmaster_es_rebotado():
    msg = EmailMessage()
    msg["From"] = "postmaster@dominio.com"
    msg.set_content("Undeliverable")
    assert classify(msg) == (EstadoEnvio.REBOTADO, False)


def test_classify_con_adjunto_pdf_es_pago():
    msg = EmailMessage()
    msg["From"] = "cliente@mail.com"
    msg.set_content("Adjunto comprobante")
    msg.add_attachment(b"%PDF-1.4 fake", maintype="application", subtype="pdf", filename="comprobante.pdf")
    assert classify(msg) == (EstadoEnvio.PAGO, True)


def test_classify_con_adjunto_imagen_es_pago():
    msg = EmailMessage()
    msg["From"] = "cliente@mail.com"
    msg.set_content("Foto del pago")
    msg.add_attachment(b"fake-image-bytes", maintype="image", subtype="png", filename="pago.png")
    assert classify(msg) == (EstadoEnvio.PAGO, True)


def test_classify_solo_texto_es_contestado():
    msg = EmailMessage()
    msg["From"] = "cliente@mail.com"
    msg.set_content("Ya voy a pagar la semana que viene")
    assert classify(msg) == (EstadoEnvio.CONTESTADO, False)
