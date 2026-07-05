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


def test_update_cliente_marca_inactivo(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    cliente = ClienteMaestro(clave_union="C020", nombre="Consorcio Veinte", email="veinte@mail.com")
    db.add(cliente)
    db.commit()

    r = client.put(
        f"/maestro/{cliente.id}",
        json={"activo": False},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["activo"] is False


def test_update_cliente_reactiva(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    cliente = ClienteMaestro(clave_union="C021", nombre="Consorcio Veintiuno", email="21@mail.com", activo=False)
    db.add(cliente)
    db.commit()

    r = client.put(
        f"/maestro/{cliente.id}",
        json={"activo": True},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["activo"] is True


def test_crear_cliente_manual(client, auth_headers):
    r = client.post(
        "/maestro",
        json={"clave_union": "C030", "nombre": "Consorcio Treinta", "email": "treinta@mail.com"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["clave_union"] == "C030"
    assert data["activo"] is True
    assert data["prefiere_no_recibir_email"] is False


def test_crear_cliente_clave_duplicada_activa_rechaza(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    db.add(ClienteMaestro(clave_union="C031", nombre="Ya Existe", email="existe@mail.com"))
    db.commit()

    r = client.post(
        "/maestro",
        json={"clave_union": "C031", "nombre": "Otro Nombre"},
        headers=auth_headers,
    )
    assert r.status_code == 409
    assert "inactivo" not in r.json()["detail"]


def test_crear_cliente_clave_duplicada_inactiva_sugiere_reactivar(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    db.add(ClienteMaestro(clave_union="C032", nombre="Inactivo", email="inactivo@mail.com", activo=False))
    db.commit()

    r = client.post(
        "/maestro",
        json={"clave_union": "C032", "nombre": "Otro Nombre"},
        headers=auth_headers,
    )
    assert r.status_code == 409
    assert "inactivo" in r.json()["detail"]


def test_crear_cliente_nombre_vacio_rechaza(client, auth_headers):
    r = client.post(
        "/maestro",
        json={"clave_union": "C033", "nombre": "   "},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_crear_cliente_requiere_auth(client):
    r = client.post("/maestro", json={"clave_union": "C034", "nombre": "X"})
    assert r.status_code in (401, 403)
