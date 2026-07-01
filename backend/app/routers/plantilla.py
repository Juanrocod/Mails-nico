from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.plantilla import PlantillaSchema
from app.services import db_config

router = APIRouter(prefix="/plantilla", tags=["plantilla"])


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
