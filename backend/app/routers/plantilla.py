import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.plantilla import PlantillaSchema
from app.services import db_config

router = APIRouter(prefix="/plantilla", tags=["plantilla"])

_LOGO_CONTENT_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
_LOGO_MAX_BYTES = 2 * 1024 * 1024


@router.get("", response_model=PlantillaSchema)
def get_plantilla(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db_config.load_plantilla(db)


@router.put("", response_model=PlantillaSchema)
def update_plantilla(
    body: PlantillaSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db_config.save_plantilla(db, body)


@router.post("/logo", response_model=PlantillaSchema)
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = _LOGO_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise HTTPException(status_code=422, detail="Formato de imagen no soportado (usar PNG, JPG o WEBP)")

    content = await file.read()
    if len(content) > _LOGO_MAX_BYTES:
        raise HTTPException(status_code=422, detail="La imagen no puede superar los 2MB")

    os.makedirs("uploads", exist_ok=True)
    filename = f"logo.{ext}"
    with open(os.path.join("uploads", filename), "wb") as f:
        f.write(content)

    if not settings.BACKEND_PUBLIC_URL:
        raise HTTPException(
            status_code=422,
            detail="Configurá BACKEND_PUBLIC_URL antes de subir un logo (necesario para que la imagen cargue en los mails).",
        )

    plantilla = db_config.load_plantilla(db)
    plantilla.logo_url = f"{settings.BACKEND_PUBLIC_URL}/uploads/{filename}"
    db.commit()
    db.refresh(plantilla)
    return plantilla
