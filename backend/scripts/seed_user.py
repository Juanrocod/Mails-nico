"""Crear usuario operario inicial. Correr una vez: python backend/scripts/seed_user.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("YAHOO_EMAIL", "placeholder@yahoo.com")
os.environ.setdefault("YAHOO_APP_PASSWORD", "placeholder")

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

USERNAME = os.environ.get("SEED_USERNAME", "operario")
PASSWORD = os.environ.get("SEED_PASSWORD", "Cambiar123!")

db = SessionLocal()
existing = db.query(User).filter(User.username == USERNAME).first()
if existing:
    print(f"Usuario '{USERNAME}' ya existe.")
else:
    user = User(username=USERNAME, hashed_password=hash_password(PASSWORD), is_active=True)
    db.add(user)
    db.commit()
    print(f"Usuario '{USERNAME}' creado con contrasena '{PASSWORD}'. Cambiarla inmediatamente.")
db.close()
