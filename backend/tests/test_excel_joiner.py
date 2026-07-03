from decimal import Decimal
from app.services.excel_parser import DeudorRow
from app.services.excel_joiner import join_deudores, PreviewData
from app.models.cliente_maestro import ClienteMaestro


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
