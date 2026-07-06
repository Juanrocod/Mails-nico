from unittest.mock import patch


def test_refrescar_seguimiento_ok(client, auth_headers):
    with patch("app.routers.seguimiento.imap_watcher._poll_inbox") as mock_poll:
        r = client.post("/seguimiento/refrescar", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    mock_poll.assert_called_once_with(mailbox_lookback_days=1)


def test_refrescar_seguimiento_falla_si_poll_inbox_lanza(client, auth_headers):
    with patch("app.routers.seguimiento.imap_watcher._poll_inbox", side_effect=RuntimeError("boom")):
        r = client.post("/seguimiento/refrescar", headers=auth_headers)
    assert r.status_code == 502


def test_refrescar_seguimiento_requiere_auth(client):
    r = client.post("/seguimiento/refrescar")
    assert r.status_code in (401, 403)


def test_respuestas_tardias_detecta_replies_de_ciclos_viejos(client, auth_headers, db):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.query(Ciclo).update({"activo": False})
    viejo = Ciclo(numero=9401, activo=False, creado_en=datetime.now(timezone.utc) - timedelta(days=15))
    activo = Ciclo(numero=9402, activo=True, creado_en=datetime.now(timezone.utc) - timedelta(days=1))
    db.add_all([viejo, activo])
    db.flush()
    # Reply DESPUES de que arranco el ciclo activo -> tardia
    db.add(Envio(
        ciclo_id=viejo.id, ciclo_numero=1, clave_union="TAR-1", nombre_consorcio="Tardio",
        email="tar1@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.CONTESTADO,
        reply_en=datetime.now(timezone.utc), actualizado_en=datetime.now(timezone.utc),
    ))
    # Reply ANTES del ciclo activo -> no cuenta
    db.add(Envio(
        ciclo_id=viejo.id, ciclo_numero=1, clave_union="TAR-2", nombre_consorcio="Viejo",
        email="tar2@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.CONTESTADO,
        reply_en=datetime.now(timezone.utc) - timedelta(days=10),
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/seguimiento/respuestas-tardias", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["ciclos"][0]["numero"] == 9401
    assert data["ciclos"][0]["count"] == 1

    db.query(Envio).filter(Envio.ciclo_id.in_([viejo.id, activo.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([viejo.id, activo.id])).delete(synchronize_session=False)
    db.commit()


def test_respuestas_tardias_sin_ciclo_activo(client, auth_headers, db):
    from app.models.ciclo import Ciclo

    db.query(Ciclo).update({"activo": False})
    db.commit()

    r = client.get("/seguimiento/respuestas-tardias", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"count": 0, "ciclos": []}
