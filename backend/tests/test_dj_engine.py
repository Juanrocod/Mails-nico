import pytest
from app.services.dj_engine import evaluar_reglas, resolver_dj_texto
from app.services.db_config import ConfigDJData


def cfg(**kwargs) -> ConfigDJData:
    defaults = dict(
        activa=True,
        incluir_texto_en_minuta=False,
        texto_alerta="",
        reglas=[],
        logica="OR",
        activar_si_requiere_conformidad=True,
    )
    defaults.update(kwargs)
    return ConfigDJData(**defaults)


DATOS = {
    "operacion": "Compra CI",
    "operador": "trader@broker.com",
    "origen": "Cliente",
    "estado": "Ejecutada",
    "moneda": "Pesos",
    "instrumento": "AL30",
    "cantidad": 350.0,
    "precio": 936.6,
    "monto": 327810.0,
    "cantidad_operada": 350.0,
    "precio_operado": 936.6,
    "requiere_conformidad": 0,
}


def test_dj_inactiva_no_aplica():
    config = cfg(activa=False)
    assert evaluar_reglas(config, DATOS) is False


def test_requiere_conformidad_activa_dj_automaticamente():
    config = cfg(activa=True, activar_si_requiere_conformidad=True)
    datos = {**DATOS, "requiere_conformidad": 1}
    assert evaluar_reglas(config, datos) is True


def test_requiere_conformidad_toggle_desactivado():
    config = cfg(activa=True, activar_si_requiere_conformidad=False)
    datos = {**DATOS, "requiere_conformidad": 1}
    # Sin reglas, no debe activar DJ aunque requiere_conformidad=1
    assert evaluar_reglas(config, datos) is False


def test_regla_texto_igual():
    config = cfg(reglas=[{"campo": "operacion", "operador": "=", "valor": "Compra CI"}])
    assert evaluar_reglas(config, DATOS) is True


def test_regla_texto_distinto():
    config = cfg(reglas=[{"campo": "operacion", "operador": "=", "valor": "Venta CI"}])
    assert evaluar_reglas(config, DATOS) is False


def test_regla_numerico_mayor():
    config = cfg(reglas=[{"campo": "monto", "operador": ">", "valor": "100000"}])
    assert evaluar_reglas(config, DATOS) is True


def test_regla_campo_invalido_ignorado():
    config = cfg(reglas=[{"campo": "campo_inexistente", "operador": "=", "valor": "x"}])
    assert evaluar_reglas(config, DATOS) is False


def test_logica_and_todas_deben_cumplirse():
    config = cfg(
        logica="AND",
        reglas=[
            {"campo": "operacion", "operador": "=", "valor": "Compra CI"},
            {"campo": "monto", "operador": ">", "valor": "1000000"},
        ],
    )
    assert evaluar_reglas(config, DATOS) is False


def test_resolver_dj_texto_con_variables():
    config = cfg(
        incluir_texto_en_minuta=True,
        texto_alerta="Cliente {cliente_nombre} operó {cantidad} de {instrumento}",
    )
    datos = {**DATOS, "cliente_nombre": "KIRIADRE OMAR"}
    texto = resolver_dj_texto(config, datos)
    assert texto == "Cliente KIRIADRE OMAR operó 350.0 de AL30"
