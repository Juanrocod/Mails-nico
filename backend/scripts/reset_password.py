"""Resetea la contraseña de un usuario existente.

Uso (apuntando a la DB que corresponda):
    DATABASE_URL=postgresql://... RESET_USERNAME=operario RESET_PASSWORD='NuevaClave123!' \
        python backend/scripts/reset_password.py

Si el usuario no existe, lo dice y no hace nada (para crear uno nuevo usar seed_user.py).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ENCRYPTION_KEY", "x" * 44)
os.environ.setdefault("YAHOO_EMAIL", "placeholder@yahoo.com")
os.environ.setdefault("YAHOO_APP_PASSWORD", "placeholder")

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402

USERNAME = os.environ.get("RESET_USERNAME", "operario")
NEW_PASSWORD = os.environ.get("RESET_PASSWORD")

if not NEW_PASSWORD:
    print("Falta RESET_PASSWORD en el entorno.")
    raise SystemExit(1)

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == USERNAME).first()
    if user is None:
        print(f"El usuario '{USERNAME}' no existe. Usá seed_user.py para crearlo.")
        raise SystemExit(1)
    user.hashed_password = hash_password(NEW_PASSWORD)
    db.commit()
    print(f"Contraseña de '{USERNAME}' actualizada correctamente.")
finally:
    db.close()
