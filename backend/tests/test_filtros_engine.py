from app.services.filtros_engine import evaluar_filtros
from app.services.db_config import ConfigFiltrosData


def cfg(**kwargs) -> ConfigFiltrosData:
    defaults = dict(reglas=[], logica="OR")
    defaults.update(kwargs)
    return ConfigFiltrosData(**defaults)


DATOS = {
    "operacion": "Transferencia",
    "operador": "kobruna425582",
    "origen": "Cliente",
    "estado": "Ejecutada",
    "moneda": "Pesos",
    "instrumento": "",
    "cantidad": -1.0,
    "precio": -1.0,
    "monto": 315000.0,
    "cantidad_operada": -1.0,
    "precio_operado": -1.0,
    "requiere_conformidad": 0,
}


def test_sin_reglas_no_filtra():
    """Sin reglas configuradas, ninguna fila se excluye."""
    assert evaluar_filtros(cfg(), DATOS) is False


def test_regla_texto_excluye_match():
    config = cfg(reglas=[{"campo": "operacion", "operador": "=", "valor": "Transferencia"}])
    assert evaluar_filtros(config, DATOS) is True


def test_regla_texto_no_excluye_sin_match():
    config = cfg(reglas=[{"campo": "operacion", "operador": "=", "valor": "Compra CI"}])
    assert evaluar_filtros(config, DATOS) is False


def test_regla_numerico_excluye():
    config = cfg(reglas=[{"campo": "cantidad", "operador": "=", "valor": "-1"}])
    assert evaluar_filtros(config, DATOS) is True


def test_logica_and_todas_deben_cumplirse():
    config = cfg(
        logica="AND",
        reglas=[
            {"campo": "operacion", "operador": "=", "valor": "Transferencia"},
            {"campo": "origen", "operador": "=", "valor": "User"},
        ],
    )
    # origen es "Cliente", no "User" → AND falla → no filtra
    assert evaluar_filtros(config, DATOS) is False


def test_logica_or_basta_una():
    config = cfg(
        logica="OR",
        reglas=[
            {"campo": "operacion", "operador": "=", "valor": "Compra CI"},
            {"campo": "origen", "operador": "=", "valor": "Cliente"},
        ],
    )
    assert evaluar_filtros(config, DATOS) is True


def test_campo_invalido_ignorado():
    config = cfg(reglas=[{"campo": "campo_raro", "operador": "=", "valor": "x"}])
    assert evaluar_filtros(config, DATOS) is False
