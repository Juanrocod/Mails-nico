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


def test_unsubscribe_url_usa_token_firmado():
    from decimal import Decimal
    from app.services.excel_joiner import EnvioParsed
    from app.models.plantilla import Plantilla
    from app.core.security import verify_unsubscribe_token

    envio = EnvioParsed(
        clave_union="C001", nombre="Consorcio Uno", email="uno@mail.com",
        localidad=None, monto=Decimal("5000"), ciclo_numero_anterior=0,
    )
    plantilla = Plantilla(
        asunto="Deuda", cuerpo_html="<p>Hola {{nombre}}</p>",
        nombre_empresa="SA", color_primario="#1a56db", monto_minimo=0,
    )
    msg = generate_email(envio, plantilla, unsubscribe_base_url="https://api.ejemplo.com")
    html = msg.get_body(preferencelist=("html",)).get_content()

    assert "clave=C001" not in html  # ya no expone la clave en texto plano
    assert "https://api.ejemplo.com/unsubscribe/" in html

    # el token embebido en el HTML debe verificar correctamente contra C001
    start = html.index("/unsubscribe/") + len("/unsubscribe/")
    end = html.index('"', start)
    token = html[start:end]
    assert verify_unsubscribe_token(token) == "C001"
