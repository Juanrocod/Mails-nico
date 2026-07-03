def test_get_configuracion_yahoo_sin_configurar(client, auth_headers):
    r = client.get("/configuracion/yahoo", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is False
    assert data["yahoo_email"] is None


def test_put_configuracion_yahoo(client, auth_headers):
    r = client.put(
        "/configuracion/yahoo",
        json={"yahoo_email": "cliente@yahoo.com", "yahoo_app_password": "abcd efgh ijkl mnop"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is True
    assert data["yahoo_email"] == "cliente@yahoo.com"
    assert "yahoo_app_password" not in data


def test_put_configuracion_yahoo_persiste(client, auth_headers):
    client.put(
        "/configuracion/yahoo",
        json={"yahoo_email": "otro@yahoo.com", "yahoo_app_password": "clave-app"},
        headers=auth_headers,
    )
    r = client.get("/configuracion/yahoo", headers=auth_headers)
    assert r.json()["yahoo_email"] == "otro@yahoo.com"
    assert r.json()["configurado"] is True


def test_get_configuracion_yahoo_requiere_auth(client):
    r = client.get("/configuracion/yahoo")
    assert r.status_code in (401, 403)


def test_put_configuracion_yahoo_rechaza_password_vacia(client, auth_headers):
    r = client.put(
        "/configuracion/yahoo",
        json={"yahoo_email": "cliente@yahoo.com", "yahoo_app_password": ""},
        headers=auth_headers,
    )
    assert r.status_code == 422
