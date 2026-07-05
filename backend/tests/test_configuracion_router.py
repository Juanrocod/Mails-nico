def test_get_configuracion_yahoo_sin_configurar(client, auth_headers):
    r = client.get("/configuracion/yahoo", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is False
    assert data["yahoo_email"] is None


def test_put_configuracion_yahoo(client, auth_headers):
    r = client.put(
        "/configuracion/yahoo",
        json={"yahoo_email": "cliente@yahoo.com", "yahoo_app_password": "abcd efgh ijkl mnop"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is True
    assert data["yahoo_email"] == "cliente@yahoo.com"
    assert "yahoo_app_password" not in data


def test_put_configuracion_yahoo_persiste(client, auth_headers):
    client.put(
        "/configuracion/yahoo",
        json={"yahoo_email": "otro@yahoo.com", "yahoo_app_password": "clave-app"},
        headers=auth_headers,
    )
    r = client.get("/configuracion/yahoo", headers=auth_headers)
    assert r.json()["yahoo_email"] == "otro@yahoo.com"
    assert r.json()["configurado"] is True


def test_get_configuracion_yahoo_requiere_auth(client):
    r = client.get("/configuracion/yahoo")
    assert r.status_code in (401, 403)


def test_put_configuracion_yahoo_rechaza_password_vacia(client, auth_headers):
    r = client.put(
        "/configuracion/yahoo",
        json={"yahoo_email": "cliente@yahoo.com", "yahoo_app_password": ""},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_get_proveedor_default_yahoo(client, auth_headers):
    r = client.get("/configuracion/proveedor", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["proveedor"] == "yahoo"


def test_put_proveedor_gmail(client, auth_headers):
    r = client.put("/configuracion/proveedor", json={"proveedor": "gmail"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["proveedor"] == "gmail"

    r2 = client.get("/configuracion/proveedor", headers=auth_headers)
    assert r2.json()["proveedor"] == "gmail"


def test_put_proveedor_invalido_rechaza(client, auth_headers):
    r = client.put("/configuracion/proveedor", json={"proveedor": "outlook"}, headers=auth_headers)
    assert r.status_code == 422


def test_get_proveedor_requiere_auth(client):
    r = client.get("/configuracion/proveedor")
    assert r.status_code in (401, 403)


def test_get_configuracion_gmail_sin_configurar(client, auth_headers):
    r = client.get("/configuracion/gmail", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is False
    assert data["gmail_email"] is None


def test_put_configuracion_gmail(client, auth_headers):
    r = client.put(
        "/configuracion/gmail",
        json={"gmail_email": "cliente@gmail.com", "gmail_app_password": "abcd efgh ijkl mnop"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is True
    assert data["gmail_email"] == "cliente@gmail.com"
    assert "gmail_app_password" not in data


def test_put_configuracion_gmail_rechaza_password_vacia(client, auth_headers):
    r = client.put(
        "/configuracion/gmail",
        json={"gmail_email": "cliente@gmail.com", "gmail_app_password": ""},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_get_configuracion_gmail_requiere_auth(client):
    r = client.get("/configuracion/gmail")
    assert r.status_code in (401, 403)


def test_get_envios_pendientes_cuenta_los_del_proveedor_activo(client, auth_headers, db):
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    baseline = client.get("/configuracion/envios-pendientes", headers=auth_headers).json()
    proveedor_activo = client.get("/configuracion/proveedor", headers=auth_headers).json()["proveedor"]

    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()

    db.add(Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="CNT-PEND-1", nombre_consorcio="Cons",
        email="cnt1@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        message_id="<cnt1@yahoo.com>", enviado_en=datetime.now(timezone.utc), proveedor=proveedor_activo,
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.add(Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="CNT-PAGO-1", nombre_consorcio="Cons2",
        email="cnt2@mail.com", monto=Decimal("2000"), estado=EstadoEnvio.PAGO,
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/configuracion/envios-pendientes", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["pendientes_proveedor_activo"] == baseline["pendientes_proveedor_activo"] + 1
    assert data["intrackeados_otro_proveedor"] == baseline["intrackeados_otro_proveedor"]

    # Este Envio queda con message_id + NO_CONTESTADO en el DB compartido en
    # memoria, lo que lo haria "activo" para el imap_watcher. Limpiar para no
    # afectar otros tests (ver comentario analogo en test_ciclos.py).
    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_get_envios_pendientes_sin_proveedor_asume_el_activo(client, auth_headers, db):
    """Envios de antes de que existiera la columna proveedor (NULL) se
    asumen mandados con el proveedor activo actual."""
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    baseline = client.get("/configuracion/envios-pendientes", headers=auth_headers).json()

    ciclo = Ciclo(numero=3, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()

    db.add(Envio(
        ciclo_id=ciclo.id, ciclo_numero=3, clave_union="CNT-SINPROV-1", nombre_consorcio="Cons",
        email="sinprov@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        message_id="<sinprov@yahoo.com>", enviado_en=datetime.now(timezone.utc), proveedor=None,
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/configuracion/envios-pendientes", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["pendientes_proveedor_activo"] == baseline["pendientes_proveedor_activo"] + 1
    assert data["intrackeados_otro_proveedor"] == baseline["intrackeados_otro_proveedor"]

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_get_envios_pendientes_cuenta_intrackeados_del_otro_proveedor(client, auth_headers, db):
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    r_proveedor = client.get("/configuracion/proveedor", headers=auth_headers)
    proveedor_activo = r_proveedor.json()["proveedor"]
    otro_proveedor = "gmail" if proveedor_activo == "yahoo" else "yahoo"

    # La fixture db limpia ConfiguracionSistema entre tests, asi que el otro
    # proveedor no tiene credenciales cargadas por default: configurarlo para
    # poder verificar que otro_proveedor_email se resuelve.
    if otro_proveedor == "gmail":
        client.put(
            "/configuracion/gmail",
            json={"gmail_email": "otroproveedor@gmail.com", "gmail_app_password": "clave-app"},
            headers=auth_headers,
        )
    else:
        client.put(
            "/configuracion/yahoo",
            json={"yahoo_email": "otroproveedor@yahoo.com", "yahoo_app_password": "clave-app"},
            headers=auth_headers,
        )

    baseline = client.get("/configuracion/envios-pendientes", headers=auth_headers).json()

    ciclo = Ciclo(numero=4, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()

    db.add(Envio(
        ciclo_id=ciclo.id, ciclo_numero=4, clave_union="CNT-OTROPROV-1", nombre_consorcio="Cons",
        email="otroprov@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        message_id="<otroprov@mail.com>", enviado_en=datetime.now(timezone.utc), proveedor=otro_proveedor,
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/configuracion/envios-pendientes", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["intrackeados_otro_proveedor"] == baseline["intrackeados_otro_proveedor"] + 1
    assert data["pendientes_proveedor_activo"] == baseline["pendientes_proveedor_activo"]
    assert data["otro_proveedor_email"] is not None

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_get_envios_pendientes_ignora_envios_nunca_enviados(client, auth_headers, db):
    """Un Envio NO_CONTESTADO sin message_id nunca se llego a mandar (fallo de
    envio), asi que un cambio de proveedor no lo afecta y no debe contarse
    en el aviso de 'envios pendientes'."""
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    baseline = client.get("/configuracion/envios-pendientes", headers=auth_headers).json()

    ciclo = Ciclo(numero=2, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()

    db.add(Envio(
        ciclo_id=ciclo.id, ciclo_numero=2, clave_union="CNT-FALLO-1", nombre_consorcio="Cons",
        email="cntfallo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/configuracion/envios-pendientes", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["pendientes_proveedor_activo"] == baseline["pendientes_proveedor_activo"]
    assert data["intrackeados_otro_proveedor"] == baseline["intrackeados_otro_proveedor"]

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_get_envios_pendientes_requiere_auth(client):
    r = client.get("/configuracion/envios-pendientes")
    assert r.status_code in (401, 403)
