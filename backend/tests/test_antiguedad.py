from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio


def _ciclo(db, numero, dias_atras):
    c = Ciclo(numero=numero, activo=False,
              creado_en=datetime.now(timezone.utc) - timedelta(days=dias_atras))
    db.add(c)
    db.flush()
    return c


def _envio(db, ciclo, clave, racha, estado=EstadoEnvio.NO_CONTESTADO, saldado=False):
    e = Envio(
        ciclo_id=ciclo.id, ciclo_numero=racha, clave_union=clave,
        nombre_consorcio=f"Cons {clave}", email=f"{clave}@mail.com",
        monto=Decimal("1000"), estado=estado,
        saldado_en=datetime.now(timezone.utc) if saldado else None,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.flush()
    return e


def _limpiar(db, ciclos):
    db.query(Envio).filter(Envio.ciclo_id.in_([c.id for c in ciclos])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([c.id for c in ciclos])).delete(synchronize_session=False)
    db.commit()


def test_deudor_desde_racha_simple(db):
    from app.services.dashboard_service import deudor_desde_por_clave

    c1 = _ciclo(db, 8801, 40)
    c2 = _ciclo(db, 8802, 10)
    _envio(db, c1, "ANT-A", 1)
    _envio(db, c2, "ANT-A", 2)
    db.commit()

    desde = deudor_desde_por_clave(db, {"ANT-A"})
    assert "ANT-A" in desde
    # arranco a deber en el ciclo mas viejo de la racha (c1, ~40 dias atras)
    assert (datetime.now(timezone.utc).replace(tzinfo=None) - desde["ANT-A"].replace(tzinfo=None)).days >= 39

    _limpiar(db, [c1, c2])


def test_deudor_desde_corta_por_saldado(db):
    from app.services.dashboard_service import deudor_desde_por_clave

    c1 = _ciclo(db, 8811, 90)
    c2 = _ciclo(db, 8812, 40)
    c3 = _ciclo(db, 8813, 10)
    _envio(db, c1, "ANT-B", 3, saldado=True)   # racha vieja cerrada
    _envio(db, c2, "ANT-B", 1)                  # arranca racha nueva
    _envio(db, c3, "ANT-B", 2)
    db.commit()

    desde = deudor_desde_por_clave(db, {"ANT-B"})
    # la racha vigente arranca en c2 (~40 dias), no en c1 (~90)
    dias = (datetime.now(timezone.utc).replace(tzinfo=None) - desde["ANT-B"].replace(tzinfo=None)).days
    assert 39 <= dias <= 45

    _limpiar(db, [c1, c2, c3])


def test_deudor_desde_corta_por_pago(db):
    from app.services.dashboard_service import deudor_desde_por_clave

    c1 = _ciclo(db, 8821, 60)
    c2 = _ciclo(db, 8822, 10)
    _envio(db, c1, "ANT-C", 4, estado=EstadoEnvio.PAGO)
    _envio(db, c2, "ANT-C", 1)
    db.commit()

    desde = deudor_desde_por_clave(db, {"ANT-C"})
    dias = (datetime.now(timezone.utc).replace(tzinfo=None) - desde["ANT-C"].replace(tzinfo=None)).days
    assert dias <= 12  # arranca en c2

    _limpiar(db, [c1, c2])


def test_deudor_desde_sin_deuda_vigente(db):
    """Si el envio mas reciente esta saldado, no hay deuda vigente -> no aparece."""
    from app.services.dashboard_service import deudor_desde_por_clave

    c1 = _ciclo(db, 8831, 30)
    _envio(db, c1, "ANT-D", 2, saldado=True)
    db.commit()

    desde = deudor_desde_por_clave(db, {"ANT-D"})
    assert "ANT-D" not in desde

    _limpiar(db, [c1])


def test_deudor_desde_claves_vacias(db):
    from app.services.dashboard_service import deudor_desde_por_clave
    assert deudor_desde_por_clave(db, set()) == {}
