from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.cliente_maestro import ClienteMaestro
from app.schemas.maestro import ClienteMaestroSchema, ClienteMaestroUpdate, MaestroUploadResponse
from app.services.excel_parser import parse_maestro, ExcelParseError
from app.services.maestro_service import merge_maestro

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
    return db.query(ClienteMaestro).order_by(ClienteMaestro.nombre).all()


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

    db.commit()
    db.refresh(cliente)
    return cliente
