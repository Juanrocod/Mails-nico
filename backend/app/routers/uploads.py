from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.audit import AccionAudit
from app.models.order import (
    Orden, ExcelUpload,
    EstadoMinuta, TipoOperacion, CondicionLiquidacion,
)
from app.models.user import User
from app.schemas.order import UploadResponse, RowErrorSchema
from app.services import audit as audit_service
from app.services.dj_engine import evaluate_dj_rules
from app.services.excel_parser import parse_excel_file
from app.services.minuta_generator import generate_minuta_text

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls"}


@router.post("/excel", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato de archivo no soportado. Se esperaba .xlsx o .xls, se recibió: '{ext}'",
        )

    file_bytes = file.file.read()

    try:
        parse_result = parse_excel_file(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ip = request.client.host if request.client else "unknown"

    excel_upload = ExcelUpload(
        usuario_id=current_user.id,
        nombre_archivo=filename,
        total_ordenes=len(parse_result.ordenes) + len(parse_result.errors),
        ordenes_validas=len(parse_result.ordenes),
        ordenes_con_error=len(parse_result.errors),
    )
    db.add(excel_upload)
    db.flush()

    for parsed in parse_result.ordenes:
        dj_template = evaluate_dj_rules(
            parsed.instrumento,
            parsed.tipo,
            parsed.moneda,
            parsed.cantidad,
            parsed.precio,
            db,
        )
        dj_texto = dj_template.texto if dj_template else None
        texto_minuta = generate_minuta_text(
            cliente_nombre=parsed.cliente_nombre,
            cuenta_comitente=parsed.cuenta_comitente,
            cuenta_cotapartista=parsed.cuenta_cotapartista,
            instrumento=parsed.instrumento,
            tipo=parsed.tipo,
            cantidad=parsed.cantidad,
            precio=parsed.precio,
            moneda=parsed.moneda,
            liquidacion=parsed.liquidacion,
            fecha_operacion=parsed.fecha_operacion,
            dj_texto=dj_texto,
        )

        # Map string enum values to ORM enum instances
        tipo_enum = TipoOperacion(parsed.tipo)
        liquidacion_enum = CondicionLiquidacion(parsed.liquidacion)

        orden = Orden(
            excel_upload_id=excel_upload.id,
            cliente_nombre=parsed.cliente_nombre,
            cliente_email=parsed.cliente_email,
            cuenta_comitente=parsed.cuenta_comitente,
            cuenta_cotapartista=parsed.cuenta_cotapartista,
            instrumento=parsed.instrumento,
            tipo=tipo_enum,
            cantidad=parsed.cantidad,
            precio=parsed.precio,
            moneda=parsed.moneda,
            liquidacion=liquidacion_enum,
            fecha_operacion=parsed.fecha_operacion,
            dj_aplicada=dj_template is not None,
            dj_tipo=dj_template.nombre if dj_template else None,
            estado=EstadoMinuta.BORRADOR,
            texto_minuta=texto_minuta,
            texto_editado=False,
        )
        db.add(orden)
        db.flush()

        audit_service.record_event(
            orden_id=orden.id,
            usuario_id=current_user.id,
            accion=AccionAudit.CREADA,
            ip_origen=ip,
            db=db,
        )

    db.commit()

    return UploadResponse(
        upload_id=str(excel_upload.id),
        nombre_archivo=filename,
        total_ordenes=excel_upload.total_ordenes,
        ordenes_validas=excel_upload.ordenes_validas,
        ordenes_con_error=excel_upload.ordenes_con_error,
        errors=[RowErrorSchema(fila=e.fila, mensaje=e.mensaje) for e in parse_result.errors],
    )
