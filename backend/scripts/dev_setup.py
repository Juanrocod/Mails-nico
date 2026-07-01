"""
Setup local dev: crea tablas SQLite y usuario operario.
Correr desde backend/: python scripts/dev_setup.py
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./dev.db")
os.environ.setdefault("SECRET_KEY", "dev_secret_key_minimo_32_caracteres_cambiar_en_produccion")
os.environ.setdefault("YAHOO_EMAIL", "placeholder@yahoo.com")
os.environ.setdefault("YAHOO_APP_PASSWORD", "placeholder")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
import app.models.user
import app.models.plantilla
import app.models.cliente_maestro
import app.models.ciclo
import app.models.envio
from app.core.security import hash_password

engine = create_engine(
    "sqlite:///./dev.db",
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def _fk(dbapi_conn, _):
    dbapi_conn.cursor().execute("PRAGMA foreign_keys=ON")

Base.metadata.create_all(engine)
print("Tablas creadas.")

Session = sessionmaker(engine)
db = Session()

from app.models.user import User

existing = db.query(User).filter_by(username="operario").first()
if existing:
    print("Usuario 'operario' ya existe.")
else:
    db.add(User(
        username="operario",
        hashed_password=hash_password("Cambiar123!"),
        is_active=True,
    ))
    db.commit()
    print("Usuario creado:")
    print("  username: operario")
    print("  password: Cambiar123!")
    print("Cambiala desde /configuracion antes de usar en produccion.")

db.close()
