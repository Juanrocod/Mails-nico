from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.session import (
    SessionMinutasResponse,
    MinutaSchema,
    EditTextoRequest,
    PlantillaSchema,
    ConfigDJSchema,
    ConfigFiltrosSchema,
)
from app.services import session_store
from app.services import db_config
from app.services.db_config import ConfigDJData, ConfigFiltrosData

router = APIRouter(tags=["session"])


@router.get("/session/minutas", response_model=SessionMinutasResponse)
def get_session_minutas(
    estado: str = "BORRADOR",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    minutas = session_store.get_minutas(str(current_user.id), estado)
    items = [MinutaSchema(**m.__dict__) for m in minutas]
    return SessionMinutasResponse(items=items, total=len(items))


@router.patch("/session/minutas/{minuta_id}/texto", response_model=MinutaSchema)
def patch_minuta_texto(
    minuta_id: str,
    body: EditTextoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = session_store.update_minuta_texto(str(current_user.id), minuta_id, body.texto_minuta)
    if updated is None:
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    return MinutaSchema(**updated.__dict__)


@router.patch("/session/minutas/{minuta_id}/enviado", response_model=MinutaSchema)
def patch_minuta_enviado(
    minuta_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = session_store.marcar_enviada(str(current_user.id), minuta_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    return MinutaSchema(**updated.__dict__)


@router.post("/session/minutas/{minuta_id}/agregar", response_model=MinutaSchema)
def post_agregar_filtrada(
    minuta_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = session_store.agregar_filtrada_a_borrador(str(current_user.id), minuta_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Minuta filtrada no encontrada")
    return MinutaSchema(**updated.__dict__)


@router.post("/session/minutas-filtradas/agregar-todas")
def post_agregar_todas_filtradas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = session_store.agregar_todas_filtradas_a_borrador(str(current_user.id))
    return {"agregadas": count}


@router.get("/plantilla", response_model=PlantillaSchema)
def get_plantilla(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PlantillaSchema(texto=db_config.load_plantilla(db))


@router.patch("/plantilla", response_model=PlantillaSchema)
def patch_plantilla(
    body: PlantillaSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_config.save_plantilla(db, body.texto)
    return body


@router.get("/config/dj", response_model=ConfigDJSchema)
def get_config_dj(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = db_config.load_config_dj(db)
    return ConfigDJSchema(
        activa=cfg.activa,
        incluir_texto_en_minuta=cfg.incluir_texto_en_minuta,
        texto_alerta=cfg.texto_alerta,
        reglas=cfg.reglas,
        logica=cfg.logica,
        activar_si_requiere_conformidad=cfg.activar_si_requiere_conformidad,
    )


@router.patch("/config/dj", response_model=ConfigDJSchema)
def patch_config_dj(
    body: ConfigDJSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_config.save_config_dj(db, ConfigDJData(
        activa=body.activa,
        incluir_texto_en_minuta=body.incluir_texto_en_minuta,
        texto_alerta=body.texto_alerta,
        reglas=[r.model_dump() for r in body.reglas],
        logica=body.logica,
        activar_si_requiere_conformidad=body.activar_si_requiere_conformidad,
    ))
    return body


@router.get("/config/filtros-minutas", response_model=ConfigFiltrosSchema)
def get_config_filtros(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = db_config.load_config_filtros(db)
    return ConfigFiltrosSchema(reglas=cfg.reglas, logica=cfg.logica)


@router.patch("/config/filtros-minutas", response_model=ConfigFiltrosSchema)
def patch_config_filtros(
    body: ConfigFiltrosSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_config.save_config_filtros(db, ConfigFiltrosData(
        reglas=[r.model_dump() for r in body.reglas],
        logica=body.logica,
    ))
    return body
