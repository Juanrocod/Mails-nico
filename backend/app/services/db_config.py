from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.plantilla import Plantilla
from app.schemas.plantilla import PlantillaSchema


def load_plantilla(db: Session) -> Plantilla:
    p = db.get(Plantilla, 1)
    if p is None:
        p = Plantilla(
            id=1,
            asunto="Recordatorio de deuda",
            cuerpo_html="<p>Estimado {{nombre}},</p><p>Le informamos que registra una deuda de ${{monto}}.</p>",
            nombre_empresa="",
            color_primario="#1a56db",
            monto_minimo=0,
            actualizado_en=datetime.now(timezone.utc),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def save_plantilla(db: Session, data: PlantillaSchema) -> Plantilla:
    p = db.get(Plantilla, 1)
    if p is None:
        p = Plantilla(id=1)
        db.add(p)
    p.asunto = data.asunto
    p.cuerpo_html = data.cuerpo_html
    p.nombre_empresa = data.nombre_empresa
    p.logo_url = data.logo_url
    p.color_primario = data.color_primario
    p.monto_minimo = data.monto_minimo
    p.actualizado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return p
