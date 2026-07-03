from datetime import datetime, timezone
from app.models.cliente_maestro import ClienteMaestro
from app.core.security import generate_unsubscribe_token


def _seed_cliente(db, clave, baja=False):
    c = ClienteMaestro(
        clave_union=clave, nombre="Consorcio Test", email="test@mail.com",
        prefiere_no_recibir_email=baja, actualizado_en=datetime.now(timezone.utc),
    )
    db.add(c)
    db.flush()
    return c


def test_unsubscribe_marca_prefiere_no_recibir_email(client, db):
    _seed_cliente(db, "C500")
    token = generate_unsubscribe_token("C500")

    r = client.get(f"/unsubscribe/{token}")

    assert r.status_code == 200
    db.expire_all()
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C500").first()
    assert cliente.prefiere_no_recibir_email is True


def test_unsubscribe_no_requiere_autenticacion(client, db):
    _seed_cliente(db, "C501")
    token = generate_unsubscribe_token("C501")
    r = client.get(f"/unsubscribe/{token}")
    assert r.status_code == 200  # sin header Authorization y funciona igual


def test_unsubscribe_token_invalido_devuelve_400(client):
    r = client.get("/unsubscribe/token-truchisimo")
    assert r.status_code == 400


def test_unsubscribe_cliente_inexistente_devuelve_404(client):
    token = generate_unsubscribe_token("NO-EXISTE")
    r = client.get(f"/unsubscribe/{token}")
    assert r.status_code == 404


def test_unsubscribe_es_idempotente(client, db):
    _seed_cliente(db, "C502", baja=True)
    token = generate_unsubscribe_token("C502")
    r = client.get(f"/unsubscribe/{token}")
    assert r.status_code == 200
    db.expire_all()
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C502").first()
    assert cliente.prefiere_no_recibir_email is True
