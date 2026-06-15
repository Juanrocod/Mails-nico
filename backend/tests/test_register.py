import secrets
from datetime import datetime, timedelta, timezone
import pyotp
import pytest

from app.models.invite_token import InviteToken


@pytest.fixture
def invite_token(db):
    token = InviteToken(
        token=secrets.token_urlsafe(32),
        tipo="invite",
        user_id=None,
        expira_en=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(token)
    db.flush()
    return token


@pytest.fixture
def expired_invite_token(db):
    token = InviteToken(
        token=secrets.token_urlsafe(32),
        tipo="invite",
        user_id=None,
        expira_en=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db.add(token)
    db.flush()
    return token


def test_register_creates_inactive_user(client, invite_token):
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": "nuevousuario",
        "password": "SecurePass123!",
    })
    assert r.status_code == 201
    data = r.json()
    assert "totp_uri" in data
    assert "setup_token" in data
    assert data["totp_uri"].startswith("otpauth://totp/")


def test_register_expired_token(client, expired_invite_token):
    r = client.post("/auth/register", json={
        "token": expired_invite_token.token,
        "username": "alguien",
        "password": "SecurePass123!",
    })
    assert r.status_code == 400


def test_register_invalid_token(client):
    r = client.post("/auth/register", json={
        "token": "tokenquenoestaenladb",
        "username": "alguien",
        "password": "SecurePass123!",
    })
    assert r.status_code == 400


def test_register_username_taken(client, invite_token, test_user):
    existing_user, _ = test_user
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": existing_user.username,
        "password": "SecurePass123!",
    })
    assert r.status_code == 409


def test_confirm_register_activates_user(client, invite_token):
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": "usuarionuevo2",
        "password": "SecurePass123!",
    })
    assert r.status_code == 201
    setup_token = r.json()["setup_token"]
    totp_uri = r.json()["totp_uri"]
    secret = totp_uri.split("secret=")[1].split("&")[0]
    code = pyotp.TOTP(secret).now()

    r = client.post("/auth/register/confirm", json={
        "setup_token": setup_token,
        "totp_code": code,
    })
    assert r.status_code == 204


def test_confirm_register_wrong_totp(client, invite_token):
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": "usuarionuevo3",
        "password": "SecurePass123!",
    })
    setup_token = r.json()["setup_token"]
    r = client.post("/auth/register/confirm", json={
        "setup_token": setup_token,
        "totp_code": "000000",
    })
    assert r.status_code == 401


def test_confirm_register_invalid_setup_token(client):
    r = client.post("/auth/register/confirm", json={
        "setup_token": "tokeninvalido",
        "totp_code": "123456",
    })
    assert r.status_code == 401


def test_full_registration_then_login(client, invite_token):
    """Flujo completo: registro -> confirmar TOTP -> login normal."""
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": "usuario_full",
        "password": "SecurePass123!",
    })
    assert r.status_code == 201
    setup_token = r.json()["setup_token"]
    totp_uri = r.json()["totp_uri"]
    secret = totp_uri.split("secret=")[1].split("&")[0]
    code = pyotp.TOTP(secret).now()

    r = client.post("/auth/register/confirm", json={
        "setup_token": setup_token,
        "totp_code": code,
    })
    assert r.status_code == 204

    r = client.post("/auth/login", json={"username": "usuario_full", "password": "SecurePass123!"})
    assert r.status_code == 200
    pending_token = r.json()["pending_token"]

    code = pyotp.TOTP(secret).now()
    r = client.post("/auth/verify-totp", json={"pending_token": pending_token, "code": code})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_reset_password_valid(client, reset_token, test_user):
    user, _ = test_user
    r = client.post("/auth/reset-password", json={
        "token": reset_token.token,
        "password": "NuevaPass456!",
    })
    assert r.status_code == 204

    r = client.post("/auth/login", json={"username": user.username, "password": "NuevaPass456!"})
    assert r.status_code == 200


def test_reset_password_invalid_token(client):
    r = client.post("/auth/reset-password", json={
        "token": "tokenquenoestaenladb",
        "password": "NuevaPass456!",
    })
    assert r.status_code == 400


def test_reset_password_token_already_used(client, reset_token, test_user):
    r = client.post("/auth/reset-password", json={
        "token": reset_token.token,
        "password": "NuevaPass456!",
    })
    assert r.status_code == 204
    r = client.post("/auth/reset-password", json={
        "token": reset_token.token,
        "password": "OtraPass789!",
    })
    assert r.status_code == 400
