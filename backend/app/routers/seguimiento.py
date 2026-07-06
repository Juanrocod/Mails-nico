import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services import imap_watcher

router = APIRouter(prefix="/seguimiento", tags=["seguimiento"])


@router.post("/refrescar")
async def refrescar_seguimiento(current_user: User = Depends(get_current_user)):
    """Dispara un poll IMAP manual (fuera del ciclo automatico de 10 min) para
    que el operario pueda revisar respuestas/rebotes al toque en vez de esperar."""
    try:
        await asyncio.get_event_loop().run_in_executor(None, imap_watcher._poll_inbox)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="No se pudo conectar al correo para revisar respuestas. Revisá las credenciales del proveedor de email.",
        ) from exc
    return {"ok": True}
