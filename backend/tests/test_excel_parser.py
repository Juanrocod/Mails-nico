import io
import pathlib
import pytest
import openpyxl
from datetime import datetime

from app.services.excel_parser import parse_excel_file, EXPECTED_COLUMNS

_HERE = pathlib.Path(__file__).parent


def make_excel(rows: list[dict]) -> bytes:
    """Construye un .xlsx en memoria con los headers del Excel real y las filas dadas."""
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = list(EXPECTED_COLUMNS.values())
    for col_idx, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_idx, value=header)
    for row_idx, row_data in enumerate(rows, 2):
        for col_idx, key in enumerate(EXPECTED_COLUMNS.keys(), 1):
            ws.cell(row=row_idx, column=col_idx, value=row_data.get(key))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


VALID_ROW = {
    "cliente_nombre": "KIRIADRE OMAR",
    "cuenta_comitente": "70164",
    "cuenta_cotapartista": "177",
    "id_orden": 100453202,
    "fecha": "16/06/2026",
    "hora": "11:12:18",
    "fecha_liquidacion": "16/06/2026",
    "operacion": "Compra CI",
    "instrumento": "AL30",
    "moneda": "Pesos",
    "cantidad": 350,
    "precio": 936.6,
    "monto": 327810,
    "estado": "Ejecutada",
    "cantidad_operada": 350,
    "precio_operado": 936.6,
    "operador": "kobruna425582",
    "origen": "Cliente",
    "asesor": "Wenceslao Jakob",
    "requiere_conformidad": 0,
}

VALID_ROW_NEGATIVE = {
    **VALID_ROW,
    "cuenta_cotapartista": "",
    "instrumento": "",
    "operacion": "Transferencia",
    "cantidad": -1,
    "precio": -1,
    "cantidad_operada": -1,
    "precio_operado": -1,
}


def test_parse_valid_row():
    result = parse_excel_file(make_excel([VALID_ROW]))
    assert len(result.ordenes) == 1
    assert len(result.errors) == 0
    o = result.ordenes[0]
    assert o.cliente_nombre == "KIRIADRE OMAR"
    assert o.cuenta_comitente == "70164"
    assert o.cuenta_cotapartista == "177"
    assert o.id_orden == 100453202
    assert o.fecha_operacion == datetime(2026, 6, 16, 11, 12, 18)
    assert o.fecha_liquidacion == "16/06/2026"
    assert o.operacion == "Compra CI"
    assert o.instrumento == "AL30"
    assert o.moneda == "Pesos"
    assert o.cantidad == 350.0
    assert o.precio == 936.6
    assert o.monto == 327810.0
    assert o.estado == "Ejecutada"
    assert o.cantidad_operada == 350.0
    assert o.precio_operado == 936.6
    assert o.operador == "kobruna425582"
    assert o.asesor == "Wenceslao Jakob"
    assert o.requiere_conformidad == 0


def test_parse_row_with_negative_sentinel_and_empty_optional():
    """Filas con cantidad/precio=-1 y campos opcionales vacíos deben parsearse sin error."""
    result = parse_excel_file(make_excel([VALID_ROW_NEGATIVE]))
    assert len(result.ordenes) == 1
    assert len(result.errors) == 0
    o = result.ordenes[0]
    assert o.cantidad == -1.0
    assert o.precio == -1.0
    assert o.cuenta_cotapartista == ""
    assert o.instrumento == ""


def test_parse_missing_column_raises():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "SoloUnaColumna"
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(ValueError, match="Columnas faltantes"):
        parse_excel_file(buf.getvalue())


def test_parse_missing_required_field_reports_error():
    bad_row = {**VALID_ROW, "cliente_nombre": ""}
    result = parse_excel_file(make_excel([VALID_ROW, bad_row]))
    assert len(result.ordenes) == 1
    assert len(result.errors) == 1
    assert result.errors[0].fila == 3


def test_parse_invalid_date_reports_error():
    bad_row = {**VALID_ROW, "fecha": "not-a-date", "hora": "00:00:00"}
    result = parse_excel_file(make_excel([bad_row]))
    assert len(result.errors) == 1


def test_parse_skips_empty_rows():
    result = parse_excel_file(make_excel([VALID_ROW, {}]))
    assert len(result.ordenes) == 1


def test_parse_real_excel():
    """Parsea el Excel modelo real del broker sin errores críticos."""
    with open(_HERE / "Operaciones_modelo.xlsx", "rb") as f:
        data = f.read()
    result = parse_excel_file(data)
    assert len(result.ordenes) > 0
    assert result.ordenes[0].cliente_nombre != ""
