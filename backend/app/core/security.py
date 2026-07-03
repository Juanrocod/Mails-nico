import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

UTC = timezone.utc
_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, expires_delta: timedelta) -> str:
    from app.core.config import settings
    expire = datetime.now(UTC) + expires_delta
    return jwt.encode({"sub": subject, "exp": expire, "type": "access"}, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(subject: str) -> str:
    from app.core.config import settings
    expire = datetime.now(UTC) + timedelta(hours=settings.REFRESH_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": subject, "exp": expire, "type": "refresh"}, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    from app.core.config import settings
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


def generate_unsubscribe_token(clave_union: str) -> str:
    from app.core.config import settings
    sig = hmac.new(settings.SECRET_KEY.encode(), clave_union.encode(), hashlib.sha256).hexdigest()
    payload = f"{clave_union}:{sig}"
    return base64.urlsafe_b64encode(payload.encode()).decode()


def verify_unsubscribe_token(token: str) -> str | None:
    from app.core.config import settings
    try:
        payload = base64.urlsafe_b64decode(token.encode()).decode()
        clave_union, sig = payload.rsplit(":", 1)
    except Exception:
        return None
    expected = hmac.new(settings.SECRET_KEY.encode(), clave_union.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return clave_union
