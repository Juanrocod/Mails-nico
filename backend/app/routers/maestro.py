from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.cliente_maestro import ClienteMaestro
from app.models.ciclo import Ciclo
from app.models.envio import Envio
from app.schemas.maestro import (
    ClienteMaestroSchema,
    ClienteMaestroUpdate,
    ClienteMaestroCreate,
    MaestroUploadResponse,
    HistorialItemSchema,
    HistorialClienteResponse,
)
from app.services.excel_parser import parse_maestro, ExcelParseError
from app.services.maestro_service import merge_maestro, crear_cliente_manual

router = APIRouter(prefix="/maestro", tags=["maestro"])


@router.post("/upload", response_model=MaestroUploadResponse)
async def upload_maestro(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        rows = parse_maestro(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return merge_maestro(db, rows)


@router.get("", response_model=list[ClienteMaestroSchema])
def get_maestro(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ClienteMaestro).order_by(ClienteMaestro.clave_union).all()


@router.post("", response_model=ClienteMaestroSchema, status_code=201)
def crear_cliente(
    payload: ClienteMaestroCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return crear_cliente_manual(db, payload.clave_union, payload.nombre, payload.email, payload.localidad)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{clave_union}/historial", response_model=HistorialClienteResponse)
def historial_cliente(
    clave_union: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == clave_union).first()
    rows = (
        db.query(Envio, Ciclo)
        .join(Ciclo, Envio.ciclo_id == Ciclo.id)
        .filter(Envio.clave_union == clave_union)
        .order_by(Ciclo.numero.desc())
        .all()
    )
    if cliente is None and not rows:
        raise HTTPException(status_code=404, detail="No hay cliente ni envios con esa clave")

    items = [
        HistorialItemSchema(
            envio_id=envio.id,
            ciclo=ciclo.numero,
            ciclo_activo=ciclo.activo,
            fecha=ciclo.creado_en,
            monto=envio.monto,
            estado=envio.estado,
            motivo_filtrado=envio.motivo_filtrado,
            recibio_mail=envio.message_id is not None,
            reply_en=envio.reply_en,
            saldado_en=envio.saldado_en,
            racha=envio.ciclo_numero,
        )
        for envio, ciclo in rows
    ]
    return HistorialClienteResponse(cliente=cliente, clave_union=clave_union, items=items)


@router.put("/{cliente_id}", response_model=ClienteMaestroSchema)
def update_cliente(
    cliente_id: UUID,
    payload: ClienteMaestroUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cliente = db.get(ClienteMaestro, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    data = payload.model_dump(exclude_unset=True)
    if "nombre" in data:
        cliente.nombre = data["nombre"].strip()
    if "email" in data:
        cliente.email = data["email"].strip() or None
    if "localidad" in data:
        cliente.localidad = (data["localidad"] or "").strip() or None
    if "prefiere_no_recibir_email" in data:
        cliente.prefiere_no_recibir_email = data["prefiere_no_recibir_email"]
    if "activo" in data:
        cliente.activo = data["activo"]

    db.commit()
    db.refresh(cliente)
    return cliente
