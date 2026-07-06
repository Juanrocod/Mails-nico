from datetime import datetime, timezone
from decimal import Decimal

from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio
from app.models.cliente_maestro import ClienteMaestro


def _make_ciclo(db, numero):
    c = Ciclo(numero=numero, activo=False, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    return c


def _make_envio(db, ciclo, clave, estado=EstadoEnvio.NO_CONTESTADO, monto="1000", saldado_en=None, ciclo_numero=1):
    e = Envio(
        ciclo_id=ciclo.id, ciclo_numero=ciclo_numero, clave_union=clave, nombre_consorcio=f"Cons {clave}",
        email=f"{clave}@mail.com", monto=Decimal(monto), estado=estado,
        saldado_en=saldado_en, actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.flush()
    return e


def test_marcar_saldados_marca_ausentes_y_no_presentes(db):
    from app.services.ciclo_service import marcar_saldados

    ciclo = _make_ciclo(db, 9001)
    ausente = _make_envio(db, ciclo, "SAL-A")
    presente = _make_envio(db, ciclo, "SAL-B")
    db.commit()

    count = marcar_saldados(db, ciclo.id, {"SAL-B"})
    db.commit()

    assert count == 1
    db.refresh(ausente)
    db.refresh(presente)
    assert ausente.saldado_en is not None
    assert presente.saldado_en is None

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_marcar_saldados_cubre_todos_los_estados(db):
    from app.services.ciclo_service import marcar_saldados

    ciclo = _make_ciclo(db, 9002)
    estados = [EstadoEnvio.NO_CONTESTADO, EstadoEnvio.CONTESTADO, EstadoEnvio.PAGO,
               EstadoEnvio.REBOTADO, EstadoEnvio.SIN_EMAIL, EstadoEnvio.FILTRADO]
    envios = [_make_envio(db, ciclo, f"SAL-EST-{i}", estado=est) for i, est in enumerate(estados)]
    db.commit()

    count = marcar_saldados(db, ciclo.id, set())
    db.commit()

    assert count == len(estados)
    for e in envios:
        db.refresh(e)
        assert e.saldado_en is not None

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_marcar_saldados_no_pisa_saldados_previos(db):
    """Un envio ya saldado en una transicion anterior conserva su fecha original."""
    from app.services.ciclo_service import marcar_saldados

    ciclo = _make_ciclo(db, 9003)
    fecha_original = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ya_saldado = _make_envio(db, ciclo, "SAL-C", saldado_en=fecha_original)
    db.commit()

    count = marcar_saldados(db, ciclo.id, set())
    db.commit()

    assert count == 0
    db.refresh(ya_saldado)
    assert ya_saldado.saldado_en.year == 2026 and ya_saldado.saldado_en.month == 1

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_racha_se_resetea_si_ultimo_envio_esta_saldado(db):
    """Un deudor que saldo (inferido) y reaparece arranca la racha de cero."""
    from app.services.excel_joiner import _ciclos_consecutivos_deudor

    ciclo = _make_ciclo(db, 9004)
    _make_envio(db, ciclo, "SAL-D", ciclo_numero=4, saldado_en=datetime.now(timezone.utc))
    db.commit()

    assert _ciclos_consecutivos_deudor(db, "SAL-D") == 0

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_racha_sigue_si_ultimo_envio_no_saldado(db):
    from app.services.excel_joiner import _ciclos_consecutivos_deudor

    ciclo = _make_ciclo(db, 9005)
    _make_envio(db, ciclo, "SAL-E", ciclo_numero=3)
    db.commit()

    assert _ciclos_consecutivos_deudor(db, "SAL-E") == 3

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_confirmar_ciclo_marca_saldados_del_anterior(client, auth_headers, db, plantilla_default):
    """Integracion: confirmar un ciclo nuevo marca saldado a quien no reaparece."""
    import io
    import openpyxl
    from unittest.mock import patch, AsyncMock

    db.query(Ciclo).update({"activo": False})
    ciclo_ant = Ciclo(numero=9006, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo_ant)
    db.flush()
    envio_que_salda = _make_envio(db, ciclo_ant, "SAL-F")
    envio_que_repite = _make_envio(db, ciclo_ant, "SAL-G")
    db.add(ClienteMaestro(clave_union="SAL-G", nombre="Repite", email="salg@mail.com",
                          actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nro cliente", "nombre", "localidad", "monto"])
    ws.append(["SAL-G", "Repite", "CABA", 2000])
    buf = io.BytesIO()
    wb.save(buf)

    with patch("app.routers.ciclos.enviar_ciclo", new_callable=AsyncMock):
        r = client.post(
            "/ciclos/confirmar",
            files={"file": ("deudores.xlsx", buf.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers,
        )
    assert r.status_code == 200

    db.expire_all()
    db.refresh(envio_que_salda)
    db.refresh(envio_que_repite)
    assert envio_que_salda.saldado_en is not None
    assert envio_que_repite.saldado_en is None

    ciclo_nuevo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    db.query(Envio).filter(Envio.ciclo_id.in_([ciclo_ant.id, ciclo_nuevo.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([ciclo_ant.id, ciclo_nuevo.id])).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "SAL-G").delete(synchronize_session=False)
    db.commit()
