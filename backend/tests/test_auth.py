def test_login_exitoso(client, test_user):
    r = client.post("/auth/login", json={"username": test_user.username, "password": "SecurePass123!"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_credenciales_invalidas(client, test_user):
    r = client.post("/auth/login", json={"username": test_user.username, "password": "wrong"})
    assert r.status_code == 401


def test_refresh(client, auth_headers, test_user):
    r = client.post("/auth/login", json={"username": test_user.username, "password": "SecurePass123!"})
    refresh_token = r.json()["refresh_token"]
    r2 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_logout(client, auth_headers):
    r = client.post("/auth/logout", headers=auth_headers)
    assert r.status_code == 204


def test_me_requiere_auth(client):
    r = client.get("/auth/me")
    assert r.status_code in (401, 404)
