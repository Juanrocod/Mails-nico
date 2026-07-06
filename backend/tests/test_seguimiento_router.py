from unittest.mock import patch


def test_refrescar_seguimiento_ok(client, auth_headers):
    with patch("app.routers.seguimiento.imap_watcher._poll_inbox") as mock_poll:
        r = client.post("/seguimiento/refrescar", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    mock_poll.assert_called_once()


def test_refrescar_seguimiento_falla_si_poll_inbox_lanza(client, auth_headers):
    with patch("app.routers.seguimiento.imap_watcher._poll_inbox", side_effect=RuntimeError("boom")):
        r = client.post("/seguimiento/refrescar", headers=auth_headers)
    assert r.status_code == 502


def test_refrescar_seguimiento_requiere_auth(client):
    r = client.post("/seguimiento/refrescar")
    assert r.status_code in (401, 403)
