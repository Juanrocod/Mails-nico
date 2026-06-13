from datetime import datetime
from app.services.minuta_generator import generate_minuta_text

BASE = dict(
    cliente_nombre="Juan Pérez",
    cuenta_comitente="12345",
    cuenta_cotapartista="67890",
    instrumento="AL30",
    tipo="COMPRA",
    cantidad=1000.0,
    precio=70.50,
    moneda="USD",
    liquidacion="24HS",
    fecha_operacion=datetime(2026, 6, 13, 10, 30),
)


def test_contains_instrument():
    assert "AL30" in generate_minuta_text(**BASE)


def test_contains_tipo():
    assert "COMPRA" in generate_minuta_text(**BASE)


def test_contains_cantidad():
    text = generate_minuta_text(**BASE)
    # 1000.0 formatted with thousands separator
    assert "1.000" in text or "1,000" in text or "1000" in text


def test_contains_precio():
    text = generate_minuta_text(**BASE)
    assert "70,50" in text or "70.50" in text or "70,5" in text


def test_contains_moneda():
    assert "USD" in generate_minuta_text(**BASE)


def test_contains_liquidacion():
    assert "24HS" in generate_minuta_text(**BASE)


def test_contains_cliente_nombre():
    assert "Juan Pérez" in generate_minuta_text(**BASE)


def test_contains_cuenta_comitente():
    assert "12345" in generate_minuta_text(**BASE)


def test_contains_fecha():
    text = generate_minuta_text(**BASE)
    # Date 2026-06-13 should appear in some format
    assert "2026" in text and "13" in text


def test_no_dj_section_without_dj():
    text = generate_minuta_text(**BASE)
    assert "DECLARACIÓN JURADA" not in text


def test_dj_section_with_dj_texto():
    text = generate_minuta_text(**BASE, dj_texto="Por la presente declaro...")
    assert "DECLARACIÓN JURADA" in text
    assert "Por la presente declaro..." in text


def test_returns_string():
    assert isinstance(generate_minuta_text(**BASE), str)


def test_dj_texto_none_means_no_dj():
    text = generate_minuta_text(**BASE, dj_texto=None)
    assert "DECLARACIÓN JURADA" not in text
