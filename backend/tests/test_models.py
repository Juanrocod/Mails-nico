def test_tables_exist(engine):
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    for t in ["users", "plantilla", "clientes_maestro", "ciclos", "envios"]:
        assert t in tables, f"Tabla faltante: {t}"
