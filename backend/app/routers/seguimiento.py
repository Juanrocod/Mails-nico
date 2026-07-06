import asyncio
from functools import partial

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.ciclo import Ciclo
from app.models.envio import Envio
from app.models.user import User
from app.schemas.seguimiento import RespuestasTardiasCiclo, RespuestasTardiasResponse
from app.services import imap_watcher

router = APIRouter(prefix="/seguimiento", tags=["seguimiento"])

_REFRESCO_MANUAL_LOOKBACK_DAYS = 1


@router.post("/refrescar")
async def refrescar_seguimiento(current_user: User = Depends(get_current_user)):
    """Dispara un poll IMAP manual (fuera del ciclo automatico de 10 min) para
    que el operario pueda revisar respuestas/rebotes al toque en vez de esperar.

    Escanea solo el ultimo dia de mensajes (en vez de los 30 dias completos
    del poll automatico) para que sea rapido; el poll automatico sigue
    revisando la ventana completa como red de seguridad."""
    poll = partial(imap_watcher._poll_inbox, mailbox_lookback_days=_REFRESCO_MANUAL_LOOKBACK_DAYS)
    try:
        await asyncio.get_event_loop().run_in_executor(None, poll)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="No se pudo conectar al correo para revisar respuestas. Revisá las credenciales del proveedor de email.",
        ) from exc
    return {"ok": True}


@router.get("/respuestas-tardias", response_model=RespuestasTardiasResponse)
def respuestas_tardias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Respuestas que llegaron despues de que arranco el ciclo activo pero
    pertenecen a envios de ciclos anteriores (aterrizan en el envio viejo y
    serian invisibles desde la vista del ciclo actual)."""
    ciclo_activo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if ciclo_activo is None:
        return RespuestasTardiasResponse(count=0, ciclos=[])

    rows = (
        db.query(Envio.ciclo_id, Ciclo.numero, func.count(Envio.id))
        .join(Ciclo, Envio.ciclo_id == Ciclo.id)
        .filter(
            Envio.ciclo_id != ciclo_activo.id,
            Envio.reply_en.isnot(None),
            Envio.reply_en >= ciclo_activo.creado_en,
        )
        .group_by(Envio.ciclo_id, Ciclo.numero)
        .all()
    )
    ciclos = [RespuestasTardiasCiclo(ciclo_id=cid, numero=num, count=cnt) for cid, num, cnt in rows]
    return RespuestasTardiasResponse(count=sum(c.count for c in ciclos), ciclos=ciclos)
