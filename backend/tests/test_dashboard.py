import pytest


XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def upload_and_get_orden_id(client, auth_headers, make_valid_excel):
    """Helper: upload Excel and return the ID of the created BORRADOR orden."""
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", make_valid_excel, XLSX_CONTENT_TYPE)},
        headers=auth_headers,
    )
    assert r.status_code == 201
    r = client.get("/dashboard/borradores", headers=auth_headers)
    return r.json()["items"][0]["id"]


def test_borradores_returns_200(client, auth_headers):
    r = client.get("/dashboard/borradores", headers=auth_headers)
    assert r.status_code == 200


def test_aprobados_returns_200(client, auth_headers):
    r = client.get("/dashboard/aprobados", headers=auth_headers)
    assert r.status_code == 200


def test_enviados_returns_200(client, auth_headers):
    r = client.get("/dashboard/enviados", headers=auth_headers)
    assert r.status_code == 200


def test_confirmados_returns_200(client, auth_headers):
    r = client.get("/dashboard/confirmados", headers=auth_headers)
    assert r.status_code == 200


def test_alertas_returns_200(client, auth_headers):
    r = client.get("/dashboard/alertas", headers=auth_headers)
    assert r.status_code == 200


def test_dashboard_response_has_correct_shape(client, auth_headers):
    r = client.get("/dashboard/borradores", headers=auth_headers)
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


def test_borradores_only_shows_borrador_state(client, auth_headers, make_valid_excel):
    # Upload creates a BORRADOR
    client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", make_valid_excel, XLSX_CONTENT_TYPE)},
        headers=auth_headers,
    )
    r = client.get("/dashboard/borradores", headers=auth_headers)
    for item in r.json()["items"]:
        assert item["estado"] == "BORRADOR"


def test_aprobados_only_shows_aprobado_state(client, auth_headers, make_valid_excel):
    # Upload → approve
    orden_id = upload_and_get_orden_id(client, auth_headers, make_valid_excel)
    client.post(f"/orders/{orden_id}/approve", headers=auth_headers)
    r = client.get("/dashboard/aprobados", headers=auth_headers)
    for item in r.json()["items"]:
        assert item["estado"] == "APROBADO"


def test_borrador_not_in_aprobados(client, auth_headers, make_valid_excel):
    # Upload creates BORRADOR — should NOT appear in aprobados
    r_upload = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", make_valid_excel, XLSX_CONTENT_TYPE)},
        headers=auth_headers,
    )
    upload_id = r_upload.json()["upload_id"]
    r = client.get("/dashboard/aprobados", headers=auth_headers)
    aprobado_ids = [item["id"] for item in r.json()["items"]]
    # Get the borrador id
    r_b = client.get("/dashboard/borradores", headers=auth_headers)
    borrador_ids = [item["id"] for item in r_b.json()["items"]]
    for bid in borrador_ids:
        assert bid not in aprobado_ids


def test_pagination_size_respected(client, auth_headers, make_valid_excel):
    # Upload two valid orders (two separate uploads)
    for _ in range(2):
        client.post(
            "/uploads/excel",
            files={"file": ("ops.xlsx", make_valid_excel, XLSX_CONTENT_TYPE)},
            headers=auth_headers,
        )
    r = client.get("/dashboard/borradores?page=1&size=1", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 1


def test_dashboard_requires_auth(client):
    for endpoint in ["borradores", "aprobados", "enviados", "confirmados", "alertas"]:
        r = client.get(f"/dashboard/{endpoint}")
        assert r.status_code == 403, f"Expected 403 for /dashboard/{endpoint}, got {r.status_code}"
