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
