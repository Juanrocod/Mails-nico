import io
from dataclasses import dataclass
from datetime import datetime


EXPECTED_COLUMNS: dict[str, str] = {
    "cliente_nombre": "Descripcion",
    "cuenta_comitente": "Comitente",
    "cuenta_cotapartista": "Cuotapartista",
    "id_orden": "Orden",
    "fecha": "Fecha",
    "hora": "Hora",
    "fecha_liquidacion": "FechaLiquidacion",
    "operacion": "Operacion",
    "instrumento": "Ticker",
    "moneda": "Moneda",
    "cantidad": "Cantidad",
    "precio": "Precio",
    "monto": "Monto",
    "estado": "Estado",
    "cantidad_operada": "CantidadOperada",
    "precio_operado": "PrecioOperado",
    "operador": "Operador",
    "origen": "Origen",
    "asesor": "Asesor",
    "requiere_conformidad": "RequiereConformidad",
}


@dataclass
class OrdenParsed:
    cliente_nombre: str
    cuenta_comitente: str
    cuenta_cotapartista: str
    id_orden: int
    fecha_operacion: datetime
    fecha_liquidacion: str
    operacion: str
    instrumento: str
    moneda: str
    cantidad: float
    precio: float
    monto: float
    estado: str
    cantidad_operada: float
    precio_operado: float
    operador: str
    origen: str
    asesor: str
    requiere_conformidad: int


@dataclass
class RowError:
    fila: int
    mensaje: str


@dataclass
class ParseResult:
    ordenes: list[OrdenParsed]
    errors: list[RowError]


def parse_excel_file(file_bytes: bytes) -> ParseResult:
    import openpyxl

    wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    headers = [ws.cell(row=1, column=col).value for col in range(1, ws.max_column + 1)]
    headers = [h.strip() if isinstance(h, str) else h for h in headers]

    expected_headers = set(EXPECTED_COLUMNS.values())
    present_headers = {h for h in headers if h is not None}
    missing = expected_headers - present_headers
    if missing:
        raise ValueError(f"Columnas faltantes: {', '.join(sorted(missing))}")

    header_to_col = {h: idx for idx, h in enumerate(headers)}
    field_to_col = {
        field: header_to_col[header]
        for field, header in EXPECTED_COLUMNS.items()
    }

    ordenes: list[OrdenParsed] = []
    errors: list[RowError] = []

    for row_idx in range(2, ws.max_row + 1):
        row_values = [ws.cell(row=row_idx, column=col).value for col in range(1, ws.max_column + 1)]

        if all(v is None for v in row_values):
            continue

        def get(field: str, _rv=row_values) -> object:
            return _rv[field_to_col[field]]

        try:
            orden = _parse_row(get)
            ordenes.append(orden)
        except ValueError as e:
            errors.append(RowError(fila=row_idx, mensaje=str(e)))

    return ParseResult(ordenes=ordenes, errors=errors)


def _parse_row(get) -> OrdenParsed:
    cliente_nombre = str(get("cliente_nombre") or "").strip()
    if not cliente_nombre:
        raise ValueError("cliente_nombre es obligatorio")

    cuenta_comitente = str(get("cuenta_comitente") or "").strip()
    if not cuenta_comitente:
        raise ValueError("cuenta_comitente es obligatoria")

    cuenta_cotapartista = str(get("cuenta_cotapartista") or "").strip()

    raw_id = get("id_orden")
    try:
        id_orden = int(raw_id)
    except (TypeError, ValueError):
        raise ValueError(f"id_orden inválido: '{raw_id}'")

    raw_fecha = str(get("fecha") or "").strip()
    raw_hora = str(get("hora") or "").strip()
    try:
        fecha_operacion = datetime.strptime(f"{raw_fecha} {raw_hora}", "%d/%m/%Y %H:%M:%S")
    except ValueError:
        raise ValueError(f"fecha/hora inválida: '{raw_fecha} {raw_hora}'")

    fecha_liquidacion = str(get("fecha_liquidacion") or "").strip()

    operacion = str(get("operacion") or "").strip()
    if not operacion:
        raise ValueError("operacion es obligatoria")

    instrumento = str(get("instrumento") or "").strip()

    moneda = str(get("moneda") or "").strip()
    if not moneda:
        raise ValueError("moneda es obligatoria")

    def parse_float(field: str) -> float:
        val = get(field)
        try:
            return float(val)
        except (TypeError, ValueError):
            raise ValueError(f"{field} debe ser un número, se recibió: '{val}'")

    cantidad = parse_float("cantidad")
    precio = parse_float("precio")
    monto = parse_float("monto")
    cantidad_operada = parse_float("cantidad_operada")
    precio_operado = parse_float("precio_operado")

    estado = str(get("estado") or "").strip()
    operador = str(get("operador") or "").strip()
    origen = str(get("origen") or "").strip()
    asesor = str(get("asesor") or "").strip()

    raw_rc = get("requiere_conformidad")
    try:
        requiere_conformidad = int(raw_rc) if raw_rc is not None else 0
    except (TypeError, ValueError):
        requiere_conformidad = 0

    return OrdenParsed(
        cliente_nombre=cliente_nombre,
        cuenta_comitente=cuenta_comitente,
        cuenta_cotapartista=cuenta_cotapartista,
        id_orden=id_orden,
        fecha_operacion=fecha_operacion,
        fecha_liquidacion=fecha_liquidacion,
        operacion=operacion,
        instrumento=instrumento,
        moneda=moneda,
        cantidad=cantidad,
        precio=precio,
        monto=monto,
        estado=estado,
        cantidad_operada=cantidad_operada,
        precio_operado=precio_operado,
        operador=operador,
        origen=origen,
        asesor=asesor,
        requiere_conformidad=requiere_conformidad,
    )
