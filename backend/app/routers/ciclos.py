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
from app.services.ciclo_service import marcar_saldados
from app.services.excel_joiner import join_deudores, revalidar_para_reenvio, revalidar_lote_para_reenvio
from app.services.excel_parser import parse_deudores, ExcelParseError
from app.services.smtp_sender import enviar_ciclo, ids_en_proceso

router = APIRouter(tags=["ciclos"])
_logger = logging.getLogger("mails_nico.ciclos")

# asyncio solo mantiene referencias debiles a las tareas creadas con
# create_task: si el generador SSE que las crea se cancela (el cliente se
# desconecta o recarga la pagina), la unica referencia fuerte a send_task
# desaparece y el recolector de basura podria matarla a mitad de un envio.
# Este set las mantiene vivas hasta que terminan solas, sin importar que pase
# con el stream que las origino.
_background_send_tasks: set = set()


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

    # Desactivar ciclo anterior si existe, y marcar saldados a los deudores
    # que no reaparecen en el Excel nuevo (inferencia de pago por ausencia).
    ciclo_anterior = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if ciclo_anterior:
        ciclo_anterior.activo = False
        db.add(ciclo_anterior)
        marcar_saldados(db, ciclo_anterior.id, {d.clave_union for d in deudores})

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
        error = None
        resultado: dict = {}
        try:
            async for chunk in _stream_envios(envios_db, db, resultado):
                yield chunk
        except Exception as exc:
            error = str(exc)
        payload = {"done": True, "total": len(envios_db), "enviados": resultado.get("enviados", 0)}
        if error:
            payload["error"] = error
        yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _stream_envios(envios_db: list[Envio], db: Session, resultado: dict):
    """Yields SSE data chunks while enviar_ciclo sends mails in the background.

    `resultado` se completa con la cantidad real de envios exitosos (distinto
    de len(envios_db), que es la cantidad intentada) para que el caller pueda
    distinguir un envio parcialmente fallido de uno completo.
    """
    sent = 0
    total = len(envios_db)
    sse_queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(envio: Envio):
        nonlocal sent
        sent += 1
        payload = json.dumps({"enviado": sent, "total": total, "id": str(envio.id)})
        await sse_queue.put(f"data: {payload}\n\n")

    send_task = asyncio.create_task(enviar_ciclo(envios_db, db, progress_callback))
    _background_send_tasks.add(send_task)
    send_task.add_done_callback(_background_send_tasks.discard)

    while not send_task.done() or not sse_queue.empty():
        try:
            chunk = sse_queue.get_nowait()
            yield chunk
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.1)

    # Propagate any exception from the send task. Shielded para que si este
    # generador se cancela justo aca, el await no le pase la cancelacion a
    # send_task (que igual sigue vivo gracias a _background_send_tasks).
    await asyncio.shield(send_task)
    resultado["enviados"] = sent


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
    en_proceso = ids_en_proceso()
    result = []
    for envio in ciclo.envios:
        schema = EnvioSchema.model_validate(envio)
        schema.en_proceso = envio.id in en_proceso
        result.append(schema)
    return result


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
    if envio.id in ids_en_proceso():
        raise HTTPException(status_code=409, detail="Este envio ya se esta mandando, esperá a que termine.")

    ok, motivo = revalidar_para_reenvio(db, envio)
    if not ok:
        raise HTTPException(status_code=400, detail=motivo)

    async def _noop(_envio: Envio) -> None:
        pass

    try:
        await enviar_ciclo([envio], db, _noop)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
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

    en_proceso = ids_en_proceso()
    saltados_en_proceso = [
        {"id": str(envio.id), "motivo": "Ya se está mandando en otro proceso."}
        for envio in fallidos
        if envio.id in en_proceso
    ]
    fallidos = [envio for envio in fallidos if envio.id not in en_proceso]

    listos, saltados = revalidar_lote_para_reenvio(db, fallidos)
    saltados = saltados_en_proceso + saltados

    async def event_generator():
        error = None
        resultado: dict = {}
        try:
            async for chunk in _stream_envios(listos, db, resultado):
                yield chunk
        except Exception as exc:
            error = str(exc)
        payload = {
            "done": True,
            "total": len(listos),
            "enviados": resultado.get("enviados", 0),
            "saltados": saltados,
        }
        if error:
            payload["error"] = error
        yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
