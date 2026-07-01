from app.core.security import hash_password, verify_password, create_access_token, decode_token
from datetime import timedelta


def test_hash_verify_password():
    h = hash_password("MiClave123!")
    assert verify_password("MiClave123!", h)
    assert not verify_password("wrong", h)


def test_access_token_roundtrip():
    token = create_access_token("user-123", timedelta(hours=1))
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
