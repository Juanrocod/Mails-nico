import io
import os

from PIL import Image

from app.core.config import settings
from app.models.plantilla import Plantilla


def _make_png_bytes(size=(10, 10)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color="red").save(buf, format="PNG")
    return buf.getvalue()


def test_upload_logo_actualiza_logo_url(client, auth_headers, plantilla_default, monkeypatch):
    monkeypatch.setattr(settings, "BACKEND_PUBLIC_URL", "https://api.tudominio.com")
    png_bytes = _make_png_bytes()
    r = client.post(
        "/plantilla/logo",
        files={"file": ("logo.png", png_bytes, "image/png")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["logo_url"] == "https://api.tudominio.com/uploads/logo.png"


def test_upload_logo_rechaza_backend_public_url_vacia(client, auth_headers, plantilla_default, db, monkeypatch):
    # Test env default: BACKEND_PUBLIC_URL="" (see Settings default in app/core/config.py).
    # Guard against test-order leakage from test_upload_logo_actualiza_logo_url.
    monkeypatch.setattr(settings, "BACKEND_PUBLIC_URL", "")
    png_bytes = _make_png_bytes()

    r = client.post(
        "/plantilla/logo",
        files={"file": ("logo.png", png_bytes, "image/png")},
        headers=auth_headers,
    )

    assert r.status_code == 422
    assert "BACKEND_PUBLIC_URL" in r.json()["detail"]

    plantilla = db.get(Plantilla, 1)
    assert plantilla.logo_url != "/uploads/logo.png"
    assert plantilla.logo_url is None or not plantilla.logo_url.startswith("/uploads/")


def test_upload_logo_rechaza_formato_no_soportado(client, auth_headers, plantilla_default):
    r = client.post(
        "/plantilla/logo",
        files={"file": ("logo.gif", b"no-es-una-imagen-real", "image/gif")},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_upload_logo_rechaza_archivo_muy_grande(client, auth_headers, plantilla_default):
    big = b"0" * (3 * 1024 * 1024)  # 3MB > límite de 2MB
    r = client.post(
        "/plantilla/logo",
        files={"file": ("logo.png", big, "image/png")},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_upload_logo_requiere_auth(client):
    png_bytes = _make_png_bytes()
    r = client.post("/plantilla/logo", files={"file": ("logo.png", png_bytes, "image/png")})
    assert r.status_code in (401, 403)
