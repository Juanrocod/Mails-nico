import pyotp


def test_change_password_valid(client, auth_headers, test_user):
    user, totp_secret = test_user
    r = client.post("/auth/change-password", json={
        "old_password": "SecurePass123!",
        "new_password": "NuevaPass456!",
    }, headers=auth_headers)
    assert r.status_code == 204

    r = client.post("/auth/login", json={"username": user.username, "password": "NuevaPass456!"})
    assert r.status_code == 200


def test_change_password_wrong_old(client, auth_headers):
    r = client.post("/auth/change-password", json={
        "old_password": "contraseñaerronea",
        "new_password": "NuevaPass456!",
    }, headers=auth_headers)
    assert r.status_code == 401


def test_change_password_requires_auth(client):
    r = client.post("/auth/change-password", json={
        "old_password": "x",
        "new_password": "y",
    })
    assert r.status_code == 403


def test_regenerate_totp_valid(client, auth_headers, test_user):
    user, totp_secret = test_user
    code = pyotp.TOTP(totp_secret).now()
    r = client.post("/auth/regenerate-totp", json={"totp_code": code}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "totp_uri" in data
    assert data["totp_uri"].startswith("otpauth://totp/")
    new_secret = data["totp_uri"].split("secret=")[1].split("&")[0]
    assert new_secret != totp_secret


def test_regenerate_totp_wrong_code(client, auth_headers):
    r = client.post("/auth/regenerate-totp", json={"totp_code": "000000"}, headers=auth_headers)
    assert r.status_code == 401


def test_regenerate_totp_requires_auth(client):
    r = client.post("/auth/regenerate-totp", json={"totp_code": "123456"})
    assert r.status_code == 403
