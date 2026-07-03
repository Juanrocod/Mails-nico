import io
from PIL import Image


def _make_png_bytes(size=(10, 10)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color="red").save(buf, format="PNG")
    return buf.getvalue()


def test_upload_logo_actualiza_logo_url(client, auth_headers, plantilla_default):
    png_bytes = _make_png_bytes()
    r = client.post(
        "/plantilla/logo",
        files={"file": ("logo.png", png_bytes, "image/png")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["logo_url"].endswith("/uploads/logo.png")


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
