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


def test_get_maestro_ordena_por_clave_union_ascendente(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    db.add(ClienteMaestro(clave_union="00000050", nombre="Zeta", email="zeta@mail.com"))
    db.add(ClienteMaestro(clave_union="00000005", nombre="Alfa", email="alfa@mail.com"))
    db.add(ClienteMaestro(clave_union="00000099", nombre="Beta", email="beta@mail.com"))
    db.commit()

    r = client.get("/maestro", headers=auth_headers)
    assert r.status_code == 200
    claves = [c["clave_union"] for c in r.json()]
    posiciones = [claves.index(k) for k in ("00000005", "00000050", "00000099")]
    assert posiciones == sorted(posiciones)


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


def test_historial_de_cliente_cross_ciclo(client, auth_headers, db):
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.cliente_maestro import ClienteMaestro
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.add(ClienteMaestro(clave_union="HIS-CLI", nombre="Consorcio Historial",
                          email="hiscli@mail.com", actualizado_en=datetime.now(timezone.utc)))
    ciclos = []
    for numero in (9301, 9302):
        c = Ciclo(numero=numero, activo=(numero == 9302), creado_en=datetime.now(timezone.utc))
        db.add(c)
        db.flush()
        ciclos.append(c)
        db.add(Envio(
            ciclo_id=c.id, ciclo_numero=numero - 9300, clave_union="HIS-CLI",
            nombre_consorcio="Consorcio Historial", email="hiscli@mail.com",
            monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
            message_id="<x@mail.com>" if numero == 9301 else None,
            actualizado_en=datetime.now(timezone.utc),
        ))
    db.commit()

    r = client.get("/maestro/HIS-CLI/historial", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["cliente"]["nombre"] == "Consorcio Historial"
    assert len(data["items"]) == 2
    assert data["items"][0]["ciclo"] == 9302  # descendente
    assert data["items"][0]["ciclo_activo"] is True
    assert data["items"][1]["recibio_mail"] is True

    for c in ciclos:
        db.query(Envio).filter(Envio.ciclo_id == c.id).delete(synchronize_session=False)
        db.query(Ciclo).filter(Ciclo.id == c.id).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "HIS-CLI").delete(synchronize_session=False)
    db.commit()


def test_historial_de_clave_sin_maestro(client, auth_headers, db):
    """Una clave con envios pero sin registro en el Maestro devuelve cliente=None."""
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    ciclo = Ciclo(numero=9303, activo=False, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    db.add(Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="HIS-SIN", nombre_consorcio="Sin Maestro",
        monto=Decimal("500"), estado=EstadoEnvio.SIN_EMAIL,
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/maestro/HIS-SIN/historial", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["cliente"] is None
    assert data["clave_union"] == "HIS-SIN"
    assert len(data["items"]) == 1

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_historial_clave_inexistente_404(client, auth_headers):
    r = client.get("/maestro/NO-EXISTE-999/historial", headers=auth_headers)
    assert r.status_code == 404


def test_historial_incluye_deudor_desde(client, auth_headers, db):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models.cliente_maestro import ClienteMaestro
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.add(ClienteMaestro(clave_union="DSD-1", nombre="Deudor Desde",
                          email="dsd1@mail.com", actualizado_en=datetime.now(timezone.utc)))
    c1 = Ciclo(numero=8941, activo=False, creado_en=datetime.now(timezone.utc) - timedelta(days=50))
    c2 = Ciclo(numero=8942, activo=True, creado_en=datetime.now(timezone.utc))
    db.add_all([c1, c2])
    db.flush()
    for ciclo, racha in ((c1, 1), (c2, 2)):
        db.add(Envio(ciclo_id=ciclo.id, ciclo_numero=racha, clave_union="DSD-1",
                     nombre_consorcio="Deudor Desde", email="dsd1@mail.com",
                     monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
                     actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    r = client.get("/maestro/DSD-1/historial", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["deudor_desde"] is not None

    db.query(Envio).filter(Envio.ciclo_id.in_([c1.id, c2.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([c1.id, c2.id])).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "DSD-1").delete(synchronize_session=False)
    db.commit()


def test_historial_deudor_desde_none_si_saldado(client, auth_headers, db):
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.cliente_maestro import ClienteMaestro
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.add(ClienteMaestro(clave_union="DSD-2", nombre="Saldado",
                          email="dsd2@mail.com", actualizado_en=datetime.now(timezone.utc)))
    c = Ciclo(numero=8943, activo=False, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    db.add(Envio(ciclo_id=c.id, ciclo_numero=1, clave_union="DSD-2", nombre_consorcio="Saldado",
                 email="dsd2@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
                 saldado_en=datetime.now(timezone.utc), actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    r = client.get("/maestro/DSD-2/historial", headers=auth_headers)
    assert r.json()["deudor_desde"] is None

    db.query(Envio).filter(Envio.ciclo_id == c.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == c.id).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "DSD-2").delete(synchronize_session=False)
    db.commit()
