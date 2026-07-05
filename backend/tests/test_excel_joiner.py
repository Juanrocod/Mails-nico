from decimal import Decimal
from app.services.excel_parser import DeudorRow
from app.services.excel_joiner import join_deudores, PreviewData
from app.models.cliente_maestro import ClienteMaestro
from app.models.envio import Envio, EstadoEnvio


def _add_cliente(db, clave, nombre, email=None, baja=False):
    c = ClienteMaestro(clave_union=clave, nombre=nombre, email=email, prefiere_no_recibir_email=baja)
    db.add(c)
    db.flush()
    return c


def test_join_deudor_con_email(db):
    _add_cliente(db, "C001", "Consorcio Uno", email="uno@mail.com")
    deudores = [DeudorRow("C001", "Consorcio Uno", "CABA", Decimal("5000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.para_enviar) == 1
    assert preview.para_enviar[0].email == "uno@mail.com"
    assert len(preview.sin_email) == 0
    assert len(preview.filtrados) == 0


def test_join_deudor_sin_match_en_maestro(db):
    deudores = [DeudorRow("C999", "Desconocido", "CABA", Decimal("1000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.sin_email) == 1
    assert preview.sin_email[0].clave_union == "C999"


def test_join_filtrado_por_monto_minimo(db):
    _add_cliente(db, "C002", "Consorcio Dos", email="dos@mail.com")
    deudores = [DeudorRow("C002", "Consorcio Dos", "CABA", Decimal("300"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("500"))
    assert len(preview.filtrados) == 1
    assert preview.filtrados[0][1] == "MONTO_MINIMO"


def test_join_filtrado_por_baja(db):
    _add_cliente(db, "C003", "Consorcio Baja", email="baja@mail.com", baja=True)
    deudores = [DeudorRow("C003", "Consorcio Baja", "CABA", Decimal("9000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.filtrados) == 1
    assert preview.filtrados[0][1] == "DADO_DE_BAJA"


def test_join_sin_email_en_maestro(db):
    _add_cliente(db, "C004", "Sin Email", email=None)
    deudores = [DeudorRow("C004", "Sin Email", "CABA", Decimal("2000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.sin_email) == 1


def test_join_email_con_formato_invalido_cae_en_sin_email(db):
    _add_cliente(db, "C010", "Consorcio Diez", email="esto-no-es-un-email")
    deudores = [DeudorRow("C010", "Consorcio Diez", "CABA", Decimal("3000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.sin_email) == 1
    assert len(preview.para_enviar) == 0


def test_join_email_valido_pasa_a_para_enviar(db):
    _add_cliente(db, "C011", "Consorcio Once", email="valido@dominio.com.ar")
    deudores = [DeudorRow("C011", "Consorcio Once", "CABA", Decimal("3000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.para_enviar) == 1
    assert len(preview.sin_email) == 0


def test_join_filtrado_por_inactivo(db):
    _add_cliente(db, "C005", "Consorcio Inactivo", email="inactivo@mail.com")
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C005").first()
    cliente.activo = False
    db.flush()

    deudores = [DeudorRow("C005", "Consorcio Inactivo", "CABA", Decimal("9000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.filtrados) == 1
    assert preview.filtrados[0][1] == "DADO_DE_BAJA"
    assert len(preview.para_enviar) == 0


def test_revalidar_para_reenvio_cliente_no_encontrado(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.services.excel_joiner import revalidar_para_reenvio

    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C030", nombre_consorcio="X",
        email=None, monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is False
    assert "no existe" in motivo


def test_revalidar_para_reenvio_dado_de_baja(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.services.excel_joiner import revalidar_para_reenvio

    _add_cliente(db, "C031", "Consorcio Baja", email="baja@mail.com", baja=True)
    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C031", nombre_consorcio="Consorcio Baja",
        email="baja@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is False
    assert "baja" in motivo.lower()


def test_revalidar_para_reenvio_inactivo(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.cliente_maestro import ClienteMaestro
    from app.services.excel_joiner import revalidar_para_reenvio

    _add_cliente(db, "C032", "Consorcio Inactivo", email="inactivo@mail.com")
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C032").first()
    cliente.activo = False
    db.flush()

    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C032", nombre_consorcio="Consorcio Inactivo",
        email="inactivo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is False
    assert "inactivo" in motivo.lower()


def test_revalidar_para_reenvio_email_invalido(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.services.excel_joiner import revalidar_para_reenvio

    _add_cliente(db, "C033", "Consorcio Email Malo", email="no-es-un-email")
    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C033", nombre_consorcio="Consorcio Email Malo",
        email="no-es-un-email", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is False
    assert "email" in motivo.lower()


def test_revalidar_para_reenvio_valido_actualiza_datos(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.services.excel_joiner import revalidar_para_reenvio

    _add_cliente(db, "C034", "Consorcio Corregido", email="corregido@mail.com")
    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C034", nombre_consorcio="Nombre Viejo",
        email="viejo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is True
    assert motivo is None
    assert envio.email == "corregido@mail.com"
    assert envio.nombre_consorcio == "Consorcio Corregido"
