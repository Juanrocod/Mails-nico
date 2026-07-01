import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test_secret_key_minimum_32_characters_here_ok")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("YAHOO_EMAIL", "test@yahoo.com")
os.environ.setdefault("YAHOO_APP_PASSWORD", "testapppassword")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.plantilla import Plantilla
from app.models.cliente_maestro import ClienteMaestro
from app.models.ciclo import Ciclo
from app.models.envio import Envio

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestingSessionLocal = sessionmaker(_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture(scope="session")
def engine(setup_test_database):
    return _engine


@pytest.fixture
def db(setup_test_database):
    session = _TestingSessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def client(db):
    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        username=f"test_{os.urandom(4).hex()}",
        hashed_password=hash_password("SecurePass123!"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def auth_headers(client, test_user):
    r = client.post("/auth/login", json={"username": test_user.username, "password": "SecurePass123!"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def plantilla_default(db):
    p = Plantilla(
        id=1,
        asunto="Recordatorio de deuda",
        cuerpo_html="<p>Estimado {{nombre}}, su deuda es ${{monto}}.</p>",
        nombre_empresa="Ascensores SA",
        color_primario="#1a56db",
        monto_minimo=0,
    )
    db.add(p)
    db.flush()
    return p
