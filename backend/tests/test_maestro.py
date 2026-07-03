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


def test_update_cliente_email_y_nombre(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    cliente = ClienteMaestro(clave_union="C010", nombre="Viejo Nombre", email="viejo@mail.com")
    db.add(cliente)
    db.commit()

    r = client.put(
        f"/maestro/{cliente.id}",
        json={"nombre": "Nuevo Nombre", "email": "nuevo@mail.com"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nombre"] == "Nuevo Nombre"
    assert data["email"] == "nuevo@mail.com"


def test_update_cliente_email_invalido_rechaza(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    cliente = ClienteMaestro(clave_union="C011", nombre="Consorcio Once", email="ok@mail.com")
    db.add(cliente)
    db.commit()

    r = client.put(
        f"/maestro/{cliente.id}",
        json={"email": "no-es-un-email"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_update_cliente_inexistente_404(client, auth_headers):
    import uuid
    r = client.put(
        f"/maestro/{uuid.uuid4()}",
        json={"nombre": "X"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_update_cliente_toggle_baja_manual(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    cliente = ClienteMaestro(clave_union="C012", nombre="Consorcio Doce", email="doce@mail.com")
    db.add(cliente)
    db.commit()

    r = client.put(
        f"/maestro/{cliente.id}",
        json={"prefiere_no_recibir_email": True},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["prefiere_no_recibir_email"] is True
