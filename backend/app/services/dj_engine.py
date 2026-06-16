from typing import Optional
from app.services.db_config import ConfigDJData

_CAMPOS_NUMERICOS = {"cantidad", "precio", "monto", "cantidad_operada", "precio_operado", "requiere_conformidad"}
_CAMPOS_TEXTO = {"operacion", "operador", "origen", "estado", "moneda", "instrumento"}
_CAMPOS_PERMITIDOS = _CAMPOS_NUMERICOS | _CAMPOS_TEXTO
_OPERADORES = {">", "<", "=", "!=", ">=", "<="}


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def evaluar_reglas(config: ConfigDJData, datos: dict) -> bool:
    if not config.activa:
        return False

    # Auto-trigger por RequiereConformidad de la plataforma
    if config.activar_si_requiere_conformidad and datos.get("requiere_conformidad") == 1:
        return True

    if not config.reglas:
        return False

    resultados = []
    for regla in config.reglas:
        campo = regla.get("campo", "")
        operador = regla.get("operador", "")
        valor = regla.get("valor", "")

        if campo not in _CAMPOS_PERMITIDOS or operador not in _OPERADORES:
            resultados.append(False)
            continue

        valor_dato = datos.get(campo)

        if campo in _CAMPOS_NUMERICOS:
            try:
                v1 = float(valor_dato)
                v2 = float(valor)
            except (TypeError, ValueError):
                resultados.append(False)
                continue
            resultados.append(_cmp_num(v1, v2, operador))
        else:
            v1 = str(valor_dato or "").strip().upper()
            v2 = str(valor or "").strip().upper()
            resultados.append(_cmp_txt(v1, v2, operador))

    if not resultados:
        return False
    return any(resultados) if config.logica == "OR" else all(resultados)


def resolver_dj_texto(config: ConfigDJData, datos: dict) -> Optional[str]:
    if not config.incluir_texto_en_minuta or not config.texto_alerta:
        return None
    return config.texto_alerta.format_map(_SafeDict(datos)) or None


def _cmp_num(v1: float, v2: float, op: str) -> bool:
    if op == ">":  return v1 > v2
    if op == "<":  return v1 < v2
    if op == "=":  return v1 == v2
    if op == "!=": return v1 != v2
    if op == ">=": return v1 >= v2
    if op == "<=": return v1 <= v2
    return False


def _cmp_txt(v1: str, v2: str, op: str) -> bool:
    if op == "=":  return v1 == v2
    if op == "!=": return v1 != v2
    return False
