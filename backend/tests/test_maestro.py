import io
import openpyxl


def _make_maestro_excel(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nro cliente", "nombre", "email", "localidad"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_upload_maestro_crea_clientes(client, auth_headers):
    excel = _make_maestro_excel([
        ["C001", "Consorcio Uno", "uno@mail.com", "CABA"],
        ["C002", "Consorcio Dos", "dos@mail.com", "GBA"],
    ])
    r = client.post(
        "/maestro/upload",
        files={"file": ("maestro.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nuevos"] == 2
    assert data["total"] == 2


def test_upload_maestro_actualiza_sin_sobreescribir_baja(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    cliente = ClienteMaestro(
        clave_union="C003",
        nombre="Consorcio Baja",
        email="baja@mail.com",
        prefiere_no_recibir_email=True,
    )
    db.add(cliente)
    db.flush()

    excel = _make_maestro_excel([["C003", "Consorcio Baja Actualizado", "nuevo@mail.com", "CABA"]])
    client.post(
        "/maestro/upload",
        files={"file": ("maestro.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    db.refresh(cliente)
    assert cliente.prefiere_no_recibir_email is True
    assert cliente.nombre == "Consorcio Baja Actualizado"


def test_get_maestro(client, auth_headers):
    r = client.get("/maestro", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
