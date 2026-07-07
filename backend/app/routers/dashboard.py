from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardResumenResponse, EvolucionCicloSchema, MorosoSchema
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=DashboardResumenResponse)
def get_resumen(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = dashboard_service.resumen(db)
    return DashboardResumenResponse(
        hay_ciclo_activo=data.hay_ciclo_activo,
        deuda_total=data.deuda_total,
        deuda_total_anterior=data.deuda_total_anterior,
        deudores=data.deudores,
        deudores_anterior=data.deudores_anterior,
        cobrado=data.cobrado,
        deuda_mas_90=data.deuda_mas_90,
    )


@router.get("/evolucion", response_model=list[EvolucionCicloSchema])
def get_evolucion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        EvolucionCicloSchema(
            numero=item.numero, fecha=item.fecha, deuda_total=item.deuda_total,
            deudores=item.deudores, cobrado=item.cobrado,
        )
        for item in dashboard_service.evolucion(db)
    ]


@router.get("/morosos", response_model=list[MorosoSchema])
def get_morosos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        MorosoSchema(
            clave_union=m.clave_union, nombre_consorcio=m.nombre_consorcio, monto=m.monto,
            deudor_desde=m.deudor_desde, ciclos_debiendo=m.ciclos_debiendo, estado=m.estado,
        )
        for m in dashboard_service.morosos(db)
    ]
