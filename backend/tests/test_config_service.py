from app.services import config_service


def test_encrypt_decrypt_roundtrip():
    original = "mi-app-password-super-secreto"
    encrypted = config_service.encrypt(original)
    assert encrypted != original
    assert config_service.decrypt(encrypted) == original


def test_encrypt_valor_vacio_devuelve_vacio():
    assert config_service.encrypt("") == ""
    assert config_service.decrypt("") == ""


def test_load_config_crea_fila_default_si_no_existe(db):
    config = config_service.load_config(db)
    assert config.id == 1
    assert config.yahoo_email is None
    assert config.yahoo_app_password_encrypted is None


def test_save_yahoo_credentials_persiste_cifrado(db):
    config_service.save_yahoo_credentials(db, "cliente@yahoo.com", "app-password-123")
    config = config_service.load_config(db)
    assert config.yahoo_email == "cliente@yahoo.com"
    assert config.yahoo_app_password_encrypted != "app-password-123"
    assert config_service.decrypt(config.yahoo_app_password_encrypted) == "app-password-123"


def test_get_yahoo_credentials_usa_db_cuando_esta_configurado(db):
    config_service.save_yahoo_credentials(db, "cliente@yahoo.com", "app-password-123")
    email, password = config_service.get_yahoo_credentials(db)
    assert email == "cliente@yahoo.com"
    assert password == "app-password-123"


def test_get_yahoo_credentials_cae_a_settings_si_no_esta_configurado(db):
    email, password = config_service.get_yahoo_credentials(db)
    # conftest.py setea estas vars de entorno como fallback de test
    assert email == "test@yahoo.com"
    assert password == "testapppassword"


def test_get_active_provider_default_yahoo(db):
    assert config_service.get_active_provider(db) == "yahoo"


def test_get_active_provider_invalido_cae_a_yahoo(db):
    config = config_service.load_config(db)
    config.proveedor_activo = "outlook"
    db.commit()
    assert config_service.get_active_provider(db) == "yahoo"


def test_save_active_provider_persiste(db):
    config_service.save_active_provider(db, "gmail")
    assert config_service.get_active_provider(db) == "gmail"


def test_save_gmail_credentials_persiste_cifrado(db):
    config_service.save_gmail_credentials(db, "cliente@gmail.com", "app-password-gmail")
    config = config_service.load_config(db)
    assert config.gmail_email == "cliente@gmail.com"
    assert config.gmail_app_password_encrypted != "app-password-gmail"
    assert config_service.decrypt(config.gmail_app_password_encrypted) == "app-password-gmail"


def test_get_gmail_credentials_usa_db_cuando_esta_configurado(db):
    config_service.save_gmail_credentials(db, "cliente@gmail.com", "app-password-gmail")
    email, password = config_service.get_gmail_credentials(db)
    assert email == "cliente@gmail.com"
    assert password == "app-password-gmail"


def test_get_gmail_credentials_cae_a_settings_si_no_esta_configurado(db):
    email, password = config_service.get_gmail_credentials(db)
    assert email == ""
    assert password == ""


def test_get_active_credentials_usa_yahoo_por_default(db):
    config_service.save_yahoo_credentials(db, "cliente@yahoo.com", "app-password-yahoo")
    email, password = config_service.get_active_credentials(db)
    assert email == "cliente@yahoo.com"
    assert password == "app-password-yahoo"


def test_get_active_credentials_usa_gmail_cuando_esta_activo(db):
    config_service.save_active_provider(db, "gmail")
    config_service.save_gmail_credentials(db, "cliente@gmail.com", "app-password-gmail")
    email, password = config_service.get_active_credentials(db)
    assert email == "cliente@gmail.com"
    assert password == "app-password-gmail"


def test_probar_conexion_sin_credenciales_reporta_no_configurado(db):
    resultado = config_service.probar_conexion(db, "yahoo")
    assert resultado["configurado"] is False
    assert resultado["smtp_ok"] is False
    assert resultado["imap_ok"] is False


def test_probar_conexion_proveedor_desconocido(db):
    resultado = config_service.probar_conexion(db, "outlook")
    assert resultado["configurado"] is False
    assert "desconocido" in resultado["error"].lower()


def test_probar_conexion_login_ok(db, monkeypatch):
    config_service.save_yahoo_credentials(db, "cliente@yahoo.com", "app-password-123")
    monkeypatch.setattr(config_service, "_probar_smtp", lambda *a: (True, None))
    monkeypatch.setattr(config_service, "_probar_imap", lambda *a: (True, None))
    resultado = config_service.probar_conexion(db, "yahoo")
    assert resultado == {
        "configurado": True, "smtp_ok": True, "imap_ok": True,
        "smtp_error": None, "imap_error": None,
    }


def test_probar_conexion_login_falla_reporta_error(db, monkeypatch):
    config_service.save_yahoo_credentials(db, "cliente@yahoo.com", "clave-mala")
    monkeypatch.setattr(config_service, "_probar_smtp", lambda *a: (False, "535 auth failed"))
    monkeypatch.setattr(config_service, "_probar_imap", lambda *a: (False, "AUTHENTICATIONFAILED"))
    resultado = config_service.probar_conexion(db, "yahoo")
    assert resultado["configurado"] is True
    assert resultado["smtp_ok"] is False
    assert resultado["imap_ok"] is False
    assert "535" in resultado["smtp_error"]
