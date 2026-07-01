from decimal import Decimal
from app.services.excel_joiner import EnvioParsed
from app.services.email_generator import generate_email


def _make_envio():
    return EnvioParsed(
        clave_union="C001",
        nombre="Consorcio Test",
        email="test@mail.com",
        localidad="CABA",
        monto=Decimal("5000.50"),
        ciclo_numero_anterior=0,
    )


def test_generate_email_tiene_asunto(plantilla_default):
    msg = generate_email(_make_envio(), plantilla_default)
    assert msg["Subject"] == plantilla_default.asunto


def test_generate_email_tiene_destinatario(plantilla_default):
    msg = generate_email(_make_envio(), plantilla_default)
    assert msg["To"] == "test@mail.com"


def test_generate_email_html_contiene_nombre(plantilla_default):
    msg = generate_email(_make_envio(), plantilla_default)
    body = msg.get_payload(decode=True)
    if body is None:
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True)
                break
    assert b"Consorcio Test" in body


def test_generate_email_html_contiene_monto(plantilla_default):
    msg = generate_email(_make_envio(), plantilla_default)
    payload = None
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            break
    if payload is None:
        payload = msg.get_payload(decode=True)
    assert b"5000" in payload
