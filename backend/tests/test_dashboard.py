from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio


def _make_envio(db, ciclo, clave, monto, message_id=None, saldado_en=None):
    e = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union=clave, nombre_consorcio=f"Cons {clave}",
        email=f"{clave}@mail.com", monto=Decimal(monto), estado=EstadoEnvio.NO_CONTESTADO,
        message_id=message_id, saldado_en=saldado_en,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.flush()
    return e


def _seed_dos_ciclos(db):
    """Ciclo anterior: DSH-A ($1000, con mail, saldado), DSH-B ($2000, con mail, repite
    bajando a $500 = pago parcial de $1500), DSH-C ($300, sin mail, repite subiendo a $800).
    Ciclo activo: DSH-B ($500), DSH-C ($800), DSH-D ($900, nuevo).
    cobrado esperado = 1000 (saldado) + 1500 (parcial B) + 0 (C subio) = 2500.
    efectividad esperada = 1 de 2 con mail saldo = 50.0.
    deuda actual = 500 + 800 + 900 = 2200. deuda anterior = 3300.
    """
    db.query(Ciclo).update({"activo": False})
    anterior = Ciclo(numero=9501, activo=False, creado_en=datetime.now(timezone.utc) - timedelta(days=15))
    activo = Ciclo(numero=9502, activo=True, creado_en=datetime.now(timezone.utc))
    db.add_all([anterior, activo])
    db.flush()
    ahora = datetime.now(timezone.utc)
    _make_envio(db, anterior, "DSH-A", "1000", message_id="<a@x>", saldado_en=ahora)
    _make_envio(db, anterior, "DSH-B", "2000", message_id="<b@x>")
    _make_envio(db, anterior, "DSH-C", "300")
    _make_envio(db, activo, "DSH-B", "500")
    _make_envio(db, activo, "DSH-C", "800")
    _make_envio(db, activo, "DSH-D", "900")
    db.commit()
    return anterior, activo


def _cleanup(db, ciclos):
    db.query(Envio).filter(Envio.ciclo_id.in_([c.id for c in ciclos])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([c.id for c in ciclos])).delete(synchronize_session=False)
    db.commit()


def test_resumen_calcula_kpis(client, auth_headers, db):
    ciclos = _seed_dos_ciclos(db)

    r = client.get("/dashboard/resumen", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["hay_ciclo_activo"] is True
    assert float(data["deuda_total"]) == 2200.0
    assert float(data["deuda_total_anterior"]) == 3300.0
    assert data["deudores"] == 3
    assert data["deudores_anterior"] == 3
    assert float(data["cobrado"]) == 2500.0
    assert "efectividad" not in data
    assert float(data["deuda_mas_90"]) == 0.0  # todas las fechas son recientes

    _cleanup(db, ciclos)


def test_resumen_sin_ciclo_activo(client, auth_headers, db):
    db.query(Ciclo).update({"activo": False})
    db.commit()

    r = client.get("/dashboard/resumen", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["hay_ciclo_activo"] is False
    assert float(data["deuda_total"]) == 0.0
    assert data["cobrado"] is None
    assert float(data["deuda_mas_90"]) == 0.0


def test_resumen_primer_ciclo_sin_anterior(client, auth_headers, db):
    db.query(Ciclo).update({"activo": False})
    solo = Ciclo(numero=9503, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(solo)
    db.flush()
    _make_envio(db, solo, "DSH-SOLO", "1200")
    db.commit()

    r = client.get("/dashboard/resumen", headers=auth_headers)
    data = r.json()
    assert float(data["deuda_total"]) == 1200.0
    assert data["deuda_total_anterior"] is None
    assert data["cobrado"] is None
    assert float(data["deuda_mas_90"]) == 0.0

    _cleanup(db, [solo])


def test_evolucion_series_por_ciclo(client, auth_headers, db):
    ciclos = _seed_dos_ciclos(db)

    r = client.get("/dashboard/evolucion", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    por_numero = {item["numero"]: item for item in data}
    assert float(por_numero[9501]["deuda_total"]) == 3300.0
    assert por_numero[9501]["deudores"] == 3
    assert por_numero[9501]["cobrado"] is None or float(por_numero[9501]["cobrado"]) == 0.0
    assert float(por_numero[9502]["deuda_total"]) == 2200.0
    assert float(por_numero[9502]["cobrado"]) == 2500.0
    numeros = [item["numero"] for item in data]
    assert numeros == sorted(numeros)  # ascendente

    _cleanup(db, ciclos)


def test_resumen_deuda_mas_90(client, auth_headers, db):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.query(Ciclo).update({"activo": False})
    viejo = Ciclo(numero=8901, activo=False,
                  creado_en=datetime.now(timezone.utc) - timedelta(days=120))
    activo = Ciclo(numero=8902, activo=True, creado_en=datetime.now(timezone.utc))
    db.add_all([viejo, activo])
    db.flush()
    # DSH90 debe hace 120 dias (racha viene del ciclo viejo, sin saldar)
    for ciclo, racha in ((viejo, 1), (activo, 2)):
        db.add(Envio(
            ciclo_id=ciclo.id, ciclo_numero=racha, clave_union="DSH90",
            nombre_consorcio="Viejo", email="dsh90@mail.com", monto=Decimal("5000"),
            estado=EstadoEnvio.NO_CONTESTADO, actualizado_en=datetime.now(timezone.utc),
        ))
    # DSHNEW debe recien este ciclo (no cuenta para +90)
    db.add(Envio(
        ciclo_id=activo.id, ciclo_numero=1, clave_union="DSHNEW",
        nombre_consorcio="Nuevo", email="dshnew@mail.com", monto=Decimal("3000"),
        estado=EstadoEnvio.NO_CONTESTADO, actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/dashboard/resumen", headers=auth_headers)
    assert float(r.json()["deuda_mas_90"]) == 5000.0

    db.query(Envio).filter(Envio.ciclo_id.in_([viejo.id, activo.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([viejo.id, activo.id])).delete(synchronize_session=False)
    db.commit()


def test_morosos_ordena_por_antiguedad(client, auth_headers, db):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.query(Ciclo).update({"activo": False})
    c1 = Ciclo(numero=8911, activo=False, creado_en=datetime.now(timezone.utc) - timedelta(days=70))
    c2 = Ciclo(numero=8912, activo=True, creado_en=datetime.now(timezone.utc))
    db.add_all([c1, c2])
    db.flush()
    # VIEJO: racha desde c1 (~70 dias). NUEVO: recien c2.
    db.add(Envio(ciclo_id=c1.id, ciclo_numero=1, clave_union="MOR-VIEJO", nombre_consorcio="Viejo",
                 email="v@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
                 actualizado_en=datetime.now(timezone.utc)))
    db.add(Envio(ciclo_id=c2.id, ciclo_numero=2, clave_union="MOR-VIEJO", nombre_consorcio="Viejo",
                 email="v@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
                 actualizado_en=datetime.now(timezone.utc)))
    db.add(Envio(ciclo_id=c2.id, ciclo_numero=1, clave_union="MOR-NUEVO", nombre_consorcio="Nuevo",
                 email="n@mail.com", monto=Decimal("2000"), estado=EstadoEnvio.NO_CONTESTADO,
                 actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    r = client.get("/dashboard/morosos", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    claves = [m["clave_union"] for m in data]
    assert claves.index("MOR-VIEJO") < claves.index("MOR-NUEVO")  # mas viejo primero
    viejo = next(m for m in data if m["clave_union"] == "MOR-VIEJO")
    assert viejo["ciclos_debiendo"] == 2

    db.query(Envio).filter(Envio.ciclo_id.in_([c1.id, c2.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([c1.id, c2.id])).delete(synchronize_session=False)
    db.commit()


def test_morosos_excluye_pagados(client, auth_headers, db):
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.query(Ciclo).update({"activo": False})
    c = Ciclo(numero=8921, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    db.add(Envio(ciclo_id=c.id, ciclo_numero=1, clave_union="MOR-PAGO", nombre_consorcio="Pago",
                 email="p@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.PAGO,
                 actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    r = client.get("/dashboard/morosos", headers=auth_headers)
    assert all(m["clave_union"] != "MOR-PAGO" for m in r.json())

    db.query(Envio).filter(Envio.ciclo_id == c.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == c.id).delete(synchronize_session=False)
    db.commit()


def test_morosos_requiere_auth(client):
    r = client.get("/dashboard/morosos")
    assert r.status_code in (401, 403)
