def test_get_plantilla_sin_datos_devuelve_defaults(client, auth_headers):
    r = client.get("/plantilla", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "asunto" in data
    assert "cuerpo_html" in data
    assert "monto_minimo" in data


def test_put_plantilla(client, auth_headers):
    payload = {
        "asunto": "Deuda pendiente",
        "cuerpo_html": "<p>Hola {{nombre}}</p>",
        "nombre_empresa": "Ascensores SA",
        "color_primario": "#ff0000",
        "monto_minimo": 1500.00,
    }
    r = client.put("/plantilla", json=payload, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["asunto"] == "Deuda pendiente"
    assert float(r.json()["monto_minimo"]) == 1500.00


def test_put_plantilla_persiste(client, auth_headers):
    client.put("/plantilla", json={
        "asunto": "Recordatorio",
        "cuerpo_html": "<p>texto</p>",
        "nombre_empresa": "SA",
        "color_primario": "#000000",
        "monto_minimo": 500,
    }, headers=auth_headers)
    r = client.get("/plantilla", headers=auth_headers)
    assert r.json()["asunto"] == "Recordatorio"


def test_put_plantilla_rechaza_palabra_prohibida_en_asunto(client, auth_headers):
    r = client.put("/plantilla", json={
        "asunto": "GRATIS: recordatorio de deuda",
        "cuerpo_html": "<p>texto normal</p>",
        "nombre_empresa": "SA",
        "color_primario": "#000000",
        "monto_minimo": 0,
    }, headers=auth_headers)
    assert r.status_code == 422


def test_put_plantilla_rechaza_palabra_prohibida_en_cuerpo(client, auth_headers):
    r = client.put("/plantilla", json={
        "asunto": "Recordatorio de deuda",
        "cuerpo_html": "<p>Haga clic ya para regularizar su situación</p>",
        "nombre_empresa": "SA",
        "color_primario": "#000000",
        "monto_minimo": 0,
    }, headers=auth_headers)
    assert r.status_code == 422


def test_put_plantilla_acepta_texto_sin_palabras_prohibidas(client, auth_headers):
    r = client.put("/plantilla", json={
        "asunto": "Recordatorio de deuda pendiente",
        "cuerpo_html": "<p>Le informamos que registra una deuda con nuestra empresa.</p>",
        "nombre_empresa": "SA",
        "color_primario": "#000000",
        "monto_minimo": 0,
    }, headers=auth_headers)
    assert r.status_code == 200
