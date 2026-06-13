import pytest

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_upload_requires_auth(client, make_valid_excel):
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", make_valid_excel, XLSX_CONTENT_TYPE)},
    )
    assert r.status_code == 403


def test_upload_valid_excel(client, auth_headers, make_valid_excel):
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", make_valid_excel, XLSX_CONTENT_TYPE)},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["ordenes_validas"] == 1
    assert data["ordenes_con_error"] == 0
    assert data["total_ordenes"] == 1
    assert data["nombre_archivo"] == "ops.xlsx"
    assert "upload_id" in data


def test_upload_non_excel_rejected(client, auth_headers):
    r = client.post(
        "/uploads/excel",
        files={"file": ("data.pdf", b"not an excel", "application/pdf")},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_upload_wrong_extension_rejected(client, auth_headers):
    r = client.post(
        "/uploads/excel",
        files={"file": ("data.csv", b"col1,col2", "text/csv")},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_upload_creates_borradores_in_dashboard(client, auth_headers, make_valid_excel):
    # Upload creates ordenes in BORRADOR state
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", make_valid_excel, XLSX_CONTENT_TYPE)},
        headers=auth_headers,
    )
    assert r.status_code == 201
    upload_id = r.json()["upload_id"]

    # The dashboard/borradores should now contain the uploaded orden
    r = client.get("/dashboard/borradores", headers=auth_headers)
    assert r.status_code == 200
    # At least one borrador exists
    assert r.json()["total"] >= 1
