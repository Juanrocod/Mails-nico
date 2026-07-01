import io
import openpyxl
from app.models.cliente_maestro import ClienteMaestro
from decimal import Decimal


def _make_deudores_excel(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nro cliente", "nombre", "localidad", "monto"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _seed_cliente(db, clave, nombre, email):
    from datetime import datetime, timezone
    c = ClienteMaestro(
        clave_union=clave,
        nombre=nombre,
        email=email,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(c)
    db.flush()


def test_preview_retorna_conteos(client, auth_headers, db, plantilla_default):
    _seed_cliente(db, "C001", "Consorcio Uno", "uno@mail.com")
    _seed_cliente(db, "C002", "Consorcio Dos", None)
    excel = _make_deudores_excel([
        ["C001", "Consorcio Uno", "CABA", 5000],
        ["C002", "Consorcio Dos", "GBA", 2000],
        ["C999", "Desconocido", "CABA", 1000],
    ])
    r = client.post(
        "/ciclos/preview",
        files={"file": ("deudores.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["para_enviar"] == 1
    assert data["sin_email"] == 2
    assert data["filtrados"] == 0
    assert data["total_deudores"] == 3


def test_preview_no_escribe_en_db(client, auth_headers, db, plantilla_default):
    from app.models.ciclo import Ciclo
    before = db.query(Ciclo).count()
    excel = _make_deudores_excel([["C001", "Test", "CABA", 5000]])
    client.post(
        "/ciclos/preview",
        files={"file": ("d.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert db.query(Ciclo).count() == before


def test_desde_api_retorna_501(client, auth_headers):
    r = client.post("/ciclos/desde-api", json={"deudores": []}, headers=auth_headers)
    assert r.status_code == 501


def test_get_envios_activo_vacio_antes_de_confirmar(client, auth_headers):
    r = client.get("/ciclos/activo/envios", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_patch_envio_estado_contestado_a_pago(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio
    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id,
        ciclo_numero=1,
        clave_union="C001",
        nombre_consorcio="Test",
        email="t@mail.com",
        monto=Decimal("1000"),
        estado=EstadoEnvio.CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()
    r = client.patch(f"/envios/{envio.id}/estado", json={"estado": "PAGO"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "PAGO"
