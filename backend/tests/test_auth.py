import pytest
from jose import jwt
from app.core.security import generate_totp_secret, hash_password
from app.models.user import User
import pyotp


def test_login_wrong_password(client, test_user):
    r = client.post("/auth/login", json={"username": test_user[0].username, "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/auth/login", json={"username": "nobody", "password": "pass"})
    assert r.status_code == 401


def test_login_returns_pending_token(client, test_user):
    r = client.post("/auth/login", json={"username": test_user[0].username, "password": "SecurePass123!"})
    assert r.status_code == 200
    data = r.json()
    assert "pending_token" in data
    assert "message" in data


def test_verify_totp_invalid_code(client, test_user):
    r = client.post("/auth/login", json={"username": test_user[0].username, "password": "SecurePass123!"})
    pending_token = r.json()["pending_token"]
    r = client.post("/auth/verify-totp", json={"pending_token": pending_token, "code": "000000"})
    assert r.status_code == 401


def test_verify_totp_invalid_pending_token(client):
    r = client.post("/auth/verify-totp", json={"pending_token": "notavalidtoken", "code": "123456"})
    assert r.status_code == 401


def test_verify_totp_returns_tokens(client, test_user):
    user, totp_secret = test_user
    r = client.post("/auth/login", json={"username": user.username, "password": "SecurePass123!"})
    pending_token = r.json()["pending_token"]
    code = pyotp.TOTP(totp_secret).now()
    r = client.post("/auth/verify-totp", json={"pending_token": pending_token, "code": code})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_returns_new_access_token(client, test_user):
    user, totp_secret = test_user
    r = client.post("/auth/login", json={"username": user.username, "password": "SecurePass123!"})
    pending_token = r.json()["pending_token"]
    code = pyotp.TOTP(totp_secret).now()
    r = client.post("/auth/verify-totp", json={"pending_token": pending_token, "code": code})
    refresh_token = r.json()["refresh_token"]
    r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_protected_endpoint_no_token(client):
    r = client.get("/session/minutas")
    assert r.status_code == 403


def test_protected_endpoint_with_valid_token(client, auth_headers):
    r = client.get("/session/minutas", headers=auth_headers)
    assert r.status_code == 200
