from app.services.db_config import ConfigFiltrosData

_CAMPOS_NUMERICOS = {"cantidad", "precio", "monto", "cantidad_operada", "precio_operado", "requiere_conformidad"}
_CAMPOS_TEXTO = {"operacion", "operador", "origen", "estado", "moneda", "instrumento"}
_CAMPOS_PERMITIDOS = _CAMPOS_NUMERICOS | _CAMPOS_TEXTO
_OPERADORES = {">", "<", "=", "!=", ">=", "<="}


def evaluar_filtros(config: ConfigFiltrosData, datos: dict) -> bool:
    """Retorna True si la fila debe ser EXCLUIDA (filtrada)."""
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
