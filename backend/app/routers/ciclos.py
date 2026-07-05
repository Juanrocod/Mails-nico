import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio, MotivoFiltrado
from app.models.user import User
from app.schemas.ciclo import PreviewItem, PreviewResponse
from app.schemas.envio import EnvioSchema, EstadoUpdateRequest
from app.services import db_config
from app.services.excel_joiner import join_deudores, revalidar_para_reenvio
from app.services.excel_parser import parse_deudores, ExcelParseError
from app.services.smtp_sender import enviar_ciclo

router = APIRouter(tags=["ciclos"])
_logger = logging.getLogger("mails_nico.ciclos")


@router.post("/ciclos/preview", response_model=PreviewResponse)
async def preview_ciclo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        deudores = parse_deudores(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    plantilla = db_config.load_plantilla(db)
    preview = join_deudores(db, deudores, plantilla.monto_minimo)
    return PreviewResponse(
        para_enviar=len(preview.para_enviar),
        sin_email=len(preview.sin_email),
        filtrados=len(preview.filtrados),
        total_deudores=len(deudores),
        monto_total_enviar=sum((e.monto for e in preview.para_enviar), start=0),
        items_para_enviar=[
            PreviewItem(
                clave_union=e.clave_union,
                nombre_consorcio=e.nombre,
                email=e.email,
                monto=e.monto,
                localidad=e.localidad,
            )
            for e in preview.para_enviar
        ],
        items_sin_email=[
            PreviewItem(
                clave_union=d.clave_union,
                nombre_consorcio=d.nombre,
                monto=d.monto,
                localidad=d.localidad,
            )
            for d in preview.sin_email
        ],
        items_filtrados=[
            PreviewItem(
                clave_union=d.clave_union,
                nombre_consorcio=d.nombre,
                monto=d.monto,
                localidad=d.localidad,
                motivo_filtrado=motivo,
            )
            for d, motivo in preview.filtrados
        ],
    )


@router.post("/ciclos/confirmar")
async def confirmar_ciclo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        deudores = parse_deudores(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    plantilla = db_config.load_plantilla(db)
    preview = join_deudores(db, deudores, plantilla.monto_minimo)

    # Desactivar ciclo anterior si existe
    ciclo_anterior = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if ciclo_anterior:
        ciclo_anterior.activo = False
        db.add(ciclo_anterior)

    ultimo_num = db.query(Ciclo).count()
    nuevo_ciclo = Ciclo(numero=ultimo_num + 1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(nuevo_ciclo)
    db.flush()

    envios_db: list[Envio] = []

    for ep in preview.para_enviar:
        e = Envio(
            ciclo_id=nuevo_ciclo.id,
            ciclo_numero=nuevo_ciclo.numero,
            clave_union=ep.clave_union,
            nombre_consorcio=ep.nombre,
            email=ep.email,
            monto=ep.monto,
            estado=EstadoEnvio.NO_CONTESTADO,
            actualizado_en=datetime.now(timezone.utc),
        )
        db.add(e)
        envios_db.append(e)

    for deudor, motivo in preview.filtrados:
        e = Envio(
            ciclo_id=nuevo_ciclo.id,
            ciclo_numero=nuevo_ciclo.numero,
            clave_union=deudor.clave_union,
            nombre_consorcio=deudor.nombre,
            monto=deudor.monto,
            estado=EstadoEnvio.FILTRADO,
            motivo_filtrado=MotivoFiltrado[motivo],
            actualizado_en=datetime.now(timezone.utc),
        )
        db.add(e)

    for deudor in preview.sin_email:
        e = Envio(
            ciclo_id=nuevo_ciclo.id,
            ciclo_numero=nuevo_ciclo.numero,
            clave_union=deudor.clave_union,
            nombre_consorcio=deudor.nombre,
            monto=deudor.monto,
            estado=EstadoEnvio.SIN_EMAIL,
            actualizado_en=datetime.now(timezone.utc),
        )
        db.add(e)

    db.commit()
    for e in envios_db:
        db.refresh(e)

    async def event_generator():
        async for chunk in _stream_envios(envios_db, db):
            yield chunk
        total = len(envios_db)
        yield f"data: {json.dumps({'done': True, 'total': total})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _stream_envios(envios_db: list[Envio], db: Session):
    """Yields SSE data chunks while enviar_ciclo sends mails in the background."""
    sent = 0
    total = len(envios_db)
    sse_queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(envio: Envio):
        nonlocal sent
        sent += 1
        payload = json.dumps({"enviado": sent, "total": total, "id": str(envio.id)})
        await sse_queue.put(f"data: {payload}\n\n")

    send_task = asyncio.create_task(enviar_ciclo(envios_db, db, progress_callback))

    while not send_task.done() or not sse_queue.empty():
        try:
            chunk = sse_queue.get_nowait()
            yield chunk
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.1)

    # Propagate any exception from the send task
    await send_task


@router.post("/ciclos/desde-api")
def desde_api(current_user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="No implementado — Fase 3")


@router.get("/ciclos/activo/envios", response_model=list[EnvioSchema])
def get_envios_activo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ciclo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if not ciclo:
        return []
    return list(ciclo.envios)


@router.patch("/envios/{envio_id}/estado", response_model=EnvioSchema)
def update_envio_estado(
    envio_id: UUID,
    body: EstadoUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    envio = db.get(Envio, envio_id)
    if not envio:
        raise HTTPException(status_code=404, detail="Envio no encontrado")
    if envio.estado != EstadoEnvio.CONTESTADO or body.estado != EstadoEnvio.PAGO:
        raise HTTPException(status_code=400, detail="Solo se permite CONTESTADO → PAGO")
    envio.estado = EstadoEnvio.PAGO
    envio.actualizado_en = datetime.now(timezone.utc)
    db.add(envio)
    db.commit()
    db.refresh(envio)
    return envio


@router.post("/envios/{envio_id}/reenviar", response_model=EnvioSchema)
async def reenviar_envio(
    envio_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    envio = db.get(Envio, envio_id)
    if envio is None:
        raise HTTPException(status_code=404, detail="Envio no encontrado")
    if envio.estado != EstadoEnvio.NO_CONTESTADO or envio.message_id:
        raise HTTPException(status_code=400, detail="Este envio no esta pendiente de reenvio")

    ok, motivo = revalidar_para_reenvio(db, envio)
    if not ok:
        raise HTTPException(status_code=400, detail=motivo)

    async def _noop(_envio: Envio) -> None:
        pass

    await enviar_ciclo([envio], db, _noop)
    db.refresh(envio)
    if not envio.message_id:
        raise HTTPException(
            status_code=502,
            detail="No se pudo enviar el mail. Revisá las credenciales del proveedor de email.",
        )
    return envio


@router.post("/ciclos/activo/reenviar-fallidos")
async def reenviar_fallidos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ciclo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if not ciclo:
        raise HTTPException(status_code=404, detail="No hay un ciclo activo")

    fallidos = (
        db.query(Envio)
        .filter(
            Envio.ciclo_id == ciclo.id,
            Envio.estado == EstadoEnvio.NO_CONTESTADO,
            Envio.message_id.is_(None),
        )
        .all()
    )

    listos: list[Envio] = []
    saltados: list[dict] = []
    for envio in fallidos:
        ok, motivo = revalidar_para_reenvio(db, envio)
        if ok:
            listos.append(envio)
        else:
            saltados.append({"id": str(envio.id), "motivo": motivo})

    async def event_generator():
        async for chunk in _stream_envios(listos, db):
            yield chunk
        total = len(listos)
        yield f"data: {json.dumps({'done': True, 'total': total, 'saltados': saltados})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
