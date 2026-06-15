import pytest
from app.services.db_config import ConfigDJData
from app.services.dj_engine import evaluar_reglas, resolver_dj_texto

DATOS = {
    "cliente_nombre": "Juan Pérez",
    "cantidad": 1500000.0,
    "precio": 250.50,
    "moneda": "USD",
    "tipo": "COMPRA",
    "liquidacion": "48HS",
    "instrumento": "AL30",
}


def test_evaluar_inactiva_siempre_false():
    cfg = ConfigDJData(activa=False, reglas=[{"campo": "cantidad", "operador": ">=", "valor": "1000000"}])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_sin_reglas_false():
    cfg = ConfigDJData(activa=True, reglas=[])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_mayor_que_pasa():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "cantidad", "operador": ">", "valor": "1000000"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_mayor_que_no_pasa():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "cantidad", "operador": ">", "valor": "2000000"}])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_mayor_igual_pasa_exacto():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "cantidad", "operador": ">=", "valor": "1500000"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_igual_texto():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "moneda", "operador": "=", "valor": "USD"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_igual_texto_case_insensitive():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "moneda", "operador": "=", "valor": "usd"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_distinto_texto():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "moneda", "operador": "!=", "valor": "ARS"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_or_una_cumple():
    cfg = ConfigDJData(activa=True, logica="OR", reglas=[
        {"campo": "cantidad", "operador": ">", "valor": "2000000"},
        {"campo": "moneda", "operador": "=", "valor": "USD"},
    ])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_and_ambas_cumplen():
    cfg = ConfigDJData(activa=True, logica="AND", reglas=[
        {"campo": "cantidad", "operador": ">=", "valor": "1000000"},
        {"campo": "moneda", "operador": "=", "valor": "USD"},
    ])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_and_una_no_cumple():
    cfg = ConfigDJData(activa=True, logica="AND", reglas=[
        {"campo": "cantidad", "operador": ">=", "valor": "1000000"},
        {"campo": "moneda", "operador": "=", "valor": "ARS"},
    ])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_campo_invalido_es_false():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "CAMPO_RARO", "operador": ">", "valor": "0"}])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_valor_no_numerico_es_false():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "cantidad", "operador": ">", "valor": "abc"}])
    assert evaluar_reglas(cfg, DATOS) is False


def test_resolver_dj_texto_none_si_no_incluir():
    cfg = ConfigDJData(activa=True, incluir_texto_en_minuta=False, texto_alerta="DJ {cliente_nombre}")
    result = resolver_dj_texto(cfg, DATOS)
    assert result is None


def test_resolver_dj_texto_interpola_variables():
    cfg = ConfigDJData(activa=True, incluir_texto_en_minuta=True,
                       texto_alerta="Declara {cliente_nombre} por {moneda}")
    result = resolver_dj_texto(cfg, DATOS)
    assert result == "Declara Juan Pérez por USD"


def test_resolver_dj_texto_deja_variable_desconocida():
    cfg = ConfigDJData(activa=True, incluir_texto_en_minuta=True,
                       texto_alerta="Hola {variable_inexistente}")
    result = resolver_dj_texto(cfg, DATOS)
    assert result == "Hola {variable_inexistente}"
