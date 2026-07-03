import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_unsubscribe_token
from app.models.cliente_maestro import ClienteMaestro

router = APIRouter(tags=["unsubscribe"])
_logger = logging.getLogger("mails_nico.unsubscribe")

_PAGINA_CONFIRMACION = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Baja confirmada</title></head>
<body style="font-family: Arial, sans-serif; max-width: 480px; margin: 60px auto; text-align: center; color: #333;">
  <h1 style="font-size: 20px;">Listo, diste de baja tu suscripción</h1>
  <p>No vas a recibir más recordatorios de cobro por mail de este remitente.</p>
</body>
</html>"""


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
def unsubscribe(token: str, db: Session = Depends(get_db)):
    clave_union = verify_unsubscribe_token(token)
    if clave_union is None:
        raise HTTPException(status_code=400, detail="Link inválido")

    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == clave_union).first()
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if not cliente.prefiere_no_recibir_email:
        cliente.prefiere_no_recibir_email = True
        db.add(cliente)
        db.commit()
        _logger.info(
            "Baja voluntaria vía unsubscribe: clave_union=%s nombre=%s",
            cliente.clave_union, cliente.nombre,
        )

    return HTMLResponse(content=_PAGINA_CONFIRMACION)
