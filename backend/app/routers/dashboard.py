from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.order import EstadoMinuta
from app.schemas.order import DashboardPage
from app.services.orders import get_orders_by_estado

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _dashboard_page(estado: EstadoMinuta, page: int, size: int, db: Session) -> DashboardPage:
    result = get_orders_by_estado(estado, db, page, size)
    return DashboardPage(**result)


@router.get("/borradores", response_model=DashboardPage)
def get_borradores(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return _dashboard_page(EstadoMinuta.BORRADOR, page, size, db)


@router.get("/aprobados", response_model=DashboardPage)
def get_aprobados(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return _dashboard_page(EstadoMinuta.APROBADO, page, size, db)


@router.get("/enviados", response_model=DashboardPage)
def get_enviados(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return _dashboard_page(EstadoMinuta.ENVIADO, page, size, db)


@router.get("/confirmados", response_model=DashboardPage)
def get_confirmados(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return _dashboard_page(EstadoMinuta.CONFIRMADO, page, size, db)


@router.get("/alertas", response_model=DashboardPage)
def get_alertas(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return _dashboard_page(EstadoMinuta.ALERTA, page, size, db)
