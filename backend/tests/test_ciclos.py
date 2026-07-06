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


def test_confirmar_ciclo_informa_enviados_reales_no_solo_intentados(client, auth_headers, db, plantilla_default):
    """Si uno de los envios falla en el momento de mandarse (el per-item
    try/except de enviar_ciclo lo traga y sigue con el resto), el 'done'
    final tiene que reportar cuantos se mandaron de verdad -- no el total
    intentado -- para que el aviso de "envio completado" no mienta."""
    import json
    from unittest.mock import patch

    _seed_cliente(db, "C160", "Consorcio Ciento Sesenta", "ok@confirmar.com")
    _seed_cliente(db, "C161", "Consorcio Ciento Sesenta y Uno", "falla@confirmar.com")

    excel = _make_deudores_excel([
        ["C160", "Consorcio Ciento Sesenta", "CABA", 5000],
        ["C161", "Consorcio Ciento Sesenta y Uno", "CABA", 5000],
    ])

    def _send_side_effect(msg, *_args, **_kwargs):
        if msg["To"] == "falla@confirmar.com":
            raise OSError("Network is unreachable")
        return "<ok@yahoo.com>"

    with patch("app.services.smtp_sender._send_single_email", side_effect=_send_side_effect):
        r = client.post(
            "/ciclos/confirmar",
            files={"file": ("deudores.xlsx", excel,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers,
        )

    assert r.status_code == 200
    lines = [line for line in r.text.splitlines() if line.startswith("data: ")]
    done_payload = json.loads(lines[-1][len("data: "):])
    assert done_payload["total"] == 2
    assert done_payload["enviados"] == 1
    assert "error" not in done_payload

    # C160 se mando de verdad (message_id real + NO_CONTESTADO): limpiar como en
    # test_reenviar_envio_exitoso para que no quede "activo" para el imap_watcher.
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio

    db.expire_all()
    ciclo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    db.query(Envio).filter(Envio.clave_union.in_(["C160", "C161"])).delete(synchronize_session=False)
    if ciclo is not None:
        db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(
        ClienteMaestro.clave_union.in_(["C160", "C161"])
    ).delete(synchronize_session=False)
    db.commit()


def test_confirmar_ciclo_informa_error_si_falla_el_envio(client, auth_headers, db, plantilla_default):
    """Si enviar_ciclo falla al preparar el envio (plantilla/proveedor/credenciales),
    el SSE final debe incluir 'error' en vez de reportar 'done' como si se
    hubiese enviado todo bien."""
    from unittest.mock import patch

    _seed_cliente(db, "C150", "Consorcio Ciento Cincuenta", "cientocincuenta@confirmar.com")
    excel = _make_deudores_excel([
        ["C150", "Consorcio Ciento Cincuenta", "CABA", 5000],
    ])

    with patch("app.services.smtp_sender.config_service.get_active_credentials", side_effect=RuntimeError("boom")):
        r = client.post(
            "/ciclos/confirmar",
            files={"file": ("deudores.xlsx", excel,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers,
        )

    assert r.status_code == 200
    assert '"error"' in r.text

    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C150").delete(synchronize_session=False)
    db.commit()


def test_reenviar_envio_no_elegible_400(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    ciclo = Ciclo(numero=201, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=201, clave_union="C201", nombre_consorcio="Ya Enviado",
        email="ya@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        message_id="<abc@yahoo.com>", enviado_en=datetime.now(timezone.utc),
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.commit()

    r = client.post(f"/envios/{envio.id}/reenviar", headers=auth_headers)
    assert r.status_code == 400

    # This Envio was committed with message_id + NO_CONTESTADO on the shared
    # in-memory DB (see test_confirmar_ciclo comment above). Clean it up so
    # downstream tests (e.g. test_imap_watcher.py) don't see a stray "active" envio.
    db.delete(envio)
    db.delete(ciclo)
    db.commit()


def test_reenviar_envio_cliente_invalido_400(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    ciclo = Ciclo(numero=202, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=202, clave_union="C202", nombre_consorcio="Sin Maestro",
        email="viejo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.commit()

    r = client.post(f"/envios/{envio.id}/reenviar", headers=auth_headers)
    assert r.status_code == 400
    assert "Maestro" in r.json()["detail"]


def test_reenviar_envio_exitoso(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from unittest.mock import patch
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio
    from app.models.cliente_maestro import ClienteMaestro

    db.add(ClienteMaestro(
        clave_union="C203", nombre="Consorcio Corregido", email="corregido@mail.com",
        actualizado_en=datetime.now(timezone.utc),
    ))
    ciclo = Ciclo(numero=203, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=203, clave_union="C203", nombre_consorcio="Nombre Viejo",
        email="viejo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.commit()

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<nuevo@yahoo.com>"
        r = client.post(f"/envios/{envio.id}/reenviar", headers=auth_headers)

    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "corregido@mail.com"
    assert data["message_id"] == "<nuevo@yahoo.com>"

    # The endpoint committed this Envio (now with message_id + NO_CONTESTADO) and
    # the seeded ClienteMaestro row to the shared in-memory DB (see test_confirmar_ciclo
    # comment above). Remove them so downstream tests (test_imap_watcher.py,
    # test_maestro.py) see clean state.
    db.query(Envio).filter(Envio.id == envio.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C203").delete(synchronize_session=False)
    db.commit()


def test_reenviar_envio_inexistente_404(client, auth_headers):
    import uuid
    r = client.post(f"/envios/{uuid.uuid4()}/reenviar", headers=auth_headers)
    assert r.status_code == 404


def test_reenviar_fallidos_mezcla_elegibles_e_inelegibles(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from unittest.mock import patch
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio
    from app.models.cliente_maestro import ClienteMaestro

    db.add(ClienteMaestro(
        clave_union="C210", nombre="Consorcio Valido", email="valido@mail.com",
        actualizado_en=datetime.now(timezone.utc),
    ))

    # Este test depende de "el" ciclo activo — desactivar cualquier otro que
    # haya quedado activo de un test anterior en esta misma corrida.
    db.query(Ciclo).update({"activo": False})
    db.flush()

    ciclo = Ciclo(numero=299, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()

    envio_ok = Envio(
        ciclo_id=ciclo.id, ciclo_numero=299, clave_union="C210", nombre_consorcio="Nombre Viejo",
        email="viejo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    envio_sin_maestro = Envio(
        ciclo_id=ciclo.id, ciclo_numero=299, clave_union="C211", nombre_consorcio="Sin Maestro",
        email="x@mail.com", monto=Decimal("2000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio_ok)
    db.add(envio_sin_maestro)
    db.commit()

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<reenv@yahoo.com>"
        r = client.post("/ciclos/activo/reenviar-fallidos", headers=auth_headers)

    assert r.status_code == 200
    body = r.text
    assert '"done"' in body
    assert '"saltados"' in body
    assert str(envio_sin_maestro.id) in body
    assert "no existe" in body

    db.expire_all()
    db.refresh(envio_ok)
    db.refresh(envio_sin_maestro)
    assert envio_ok.message_id == "<reenv@yahoo.com>"
    assert envio_sin_maestro.message_id is None

    # The endpoint committed envio_ok (now with message_id + NO_CONTESTADO) and
    # the seeded ClienteMaestro row to the shared in-memory DB (see
    # test_confirmar_ciclo comment above). Remove them so downstream tests
    # (test_imap_watcher.py, test_maestro.py) see clean state.
    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C210").delete(synchronize_session=False)
    db.commit()


def test_get_envios_activo_marca_en_proceso(client, auth_headers, db, plantilla_default):
    """Un Envio cuyo id esta en smtp_sender.ids_en_proceso() (un envio en
    curso todavia no le llego el turno) tiene que aparecer con en_proceso=True,
    para que el frontend no lo trate como "fallido" listo para reenviar."""
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio
    from app.services import smtp_sender

    db.query(Ciclo).update({"activo": False})
    db.flush()
    ciclo = Ciclo(numero=401, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=401, clave_union="C401", nombre_consorcio="En Curso",
        email="encurso@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.commit()

    smtp_sender._ids_en_proceso.add(envio.id)
    try:
        r = client.get("/ciclos/activo/envios", headers=auth_headers)
    finally:
        smtp_sender._ids_en_proceso.discard(envio.id)

    assert r.status_code == 200
    by_id = {e["id"]: e for e in r.json()}
    assert by_id[str(envio.id)]["en_proceso"] is True

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_reenviar_envio_rechaza_si_ya_esta_en_proceso(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio
    from app.models.cliente_maestro import ClienteMaestro
    from app.services import smtp_sender

    db.add(ClienteMaestro(
        clave_union="C402", nombre="Consorcio En Curso", email="encurso402@mail.com",
        actualizado_en=datetime.now(timezone.utc),
    ))
    ciclo = Ciclo(numero=402, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=402, clave_union="C402", nombre_consorcio="En Curso",
        email="encurso402@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.commit()

    smtp_sender._ids_en_proceso.add(envio.id)
    try:
        r = client.post(f"/envios/{envio.id}/reenviar", headers=auth_headers)
    finally:
        smtp_sender._ids_en_proceso.discard(envio.id)

    assert r.status_code == 409

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C402").delete(synchronize_session=False)
    db.commit()


def test_reenviar_fallidos_saltea_los_que_ya_estan_en_proceso(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from unittest.mock import patch
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio
    from app.models.cliente_maestro import ClienteMaestro
    from app.services import smtp_sender

    db.add(ClienteMaestro(
        clave_union="C403", nombre="Consorcio Listo", email="listo403@mail.com",
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.add(ClienteMaestro(
        clave_union="C404", nombre="Consorcio En Curso", email="encurso404@mail.com",
        actualizado_en=datetime.now(timezone.utc),
    ))

    db.query(Ciclo).update({"activo": False})
    db.flush()
    ciclo = Ciclo(numero=403, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()

    envio_listo = Envio(
        ciclo_id=ciclo.id, ciclo_numero=403, clave_union="C403", nombre_consorcio="Consorcio Listo",
        email="listo403@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    envio_en_curso = Envio(
        ciclo_id=ciclo.id, ciclo_numero=403, clave_union="C404", nombre_consorcio="Consorcio En Curso",
        email="encurso404@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio_listo)
    db.add(envio_en_curso)
    db.commit()

    smtp_sender._ids_en_proceso.add(envio_en_curso.id)
    try:
        with patch("app.services.smtp_sender._send_single_email") as mock_send:
            mock_send.return_value = "<reenv403@yahoo.com>"
            r = client.post("/ciclos/activo/reenviar-fallidos", headers=auth_headers)
    finally:
        smtp_sender._ids_en_proceso.discard(envio_en_curso.id)

    assert r.status_code == 200
    body = r.text
    assert str(envio_en_curso.id) in body
    assert "otro proceso" in body

    db.expire_all()
    db.refresh(envio_listo)
    db.refresh(envio_en_curso)
    assert envio_listo.message_id == "<reenv403@yahoo.com>"
    assert envio_en_curso.message_id is None

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(
        ClienteMaestro.clave_union.in_(["C403", "C404"])
    ).delete(synchronize_session=False)
    db.commit()
