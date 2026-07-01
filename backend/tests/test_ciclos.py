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


def test_confirmar_ciclo(client, auth_headers, db, plantilla_default):
    """POST /ciclos/confirmar creates Ciclo + Envios with correct estados and streams SSE."""
    from unittest.mock import patch, AsyncMock
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    # Raise monto_minimo so C002 (monto=500) lands in FILTRADO / MONTO_MINIMO
    plantilla_default.monto_minimo = 1000
    db.flush()

    # Use claves that no other test commits, to avoid UNIQUE violations on the
    # shared in-memory DB (the router's db.commit() persists these records).
    # C101 → email match + monto OK → NO_CONTESTADO
    _seed_cliente(db, "C101", "Consorcio Ciento Uno", "ciento_uno@confirmar.com")
    # C102 → email match but monto 500 < 1000 → FILTRADO / MONTO_MINIMO
    _seed_cliente(db, "C102", "Consorcio Ciento Dos", "ciento_dos@confirmar.com")
    # C199 → no maestro entry → SIN_EMAIL

    excel = _make_deudores_excel([
        ["C101", "Consorcio Ciento Uno", "CABA", 5000],
        ["C102", "Consorcio Ciento Dos", "CABA", 500],
        ["C199", "Desconocido Cien",     "CABA", 3000],
    ])

    with patch("app.routers.ciclos.enviar_ciclo", new_callable=AsyncMock):
        r = client.post(
            "/ciclos/confirmar",
            files={"file": ("deudores.xlsx", excel,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers,
        )

    # --- HTTP assertions ---
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    body = r.text
    assert '"done"' in body
    assert "true" in body

    # --- DB assertions ---
    db.expire_all()

    ciclo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    assert ciclo is not None, "Expected an active Ciclo after confirmar"

    envios = db.query(Envio).filter(Envio.ciclo_id == ciclo.id).all()
    assert len(envios) == 3

    by_clave = {e.clave_union: e for e in envios}
    assert by_clave["C101"].estado == EstadoEnvio.NO_CONTESTADO
    assert by_clave["C102"].estado == EstadoEnvio.FILTRADO
    assert by_clave["C199"].estado == EstadoEnvio.SIN_EMAIL

    # The router's db.commit() also committed the seeded ClienteMaestro rows.
    # Remove them so downstream tests (test_maestro.py) see a clean maestro table.
    db.query(ClienteMaestro).filter(
        ClienteMaestro.clave_union.in_(["C101", "C102"])
    ).delete(synchronize_session=False)
    db.commit()
