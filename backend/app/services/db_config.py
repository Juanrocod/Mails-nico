import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.plantilla import Plantilla

DEFAULT_PLANTILLA = (
    "MINUTA DE OPERACIÓN Nº {id_orden}\n"
    "Fecha de operación: {fecha_operacion}\n"
    "Fecha de liquidación: {fecha_liquidacion}\n"
    "\n"
    "Estimado/a {cliente_nombre},\n"
    "\n"
    "Por medio de la presente le informamos que se ha procesado la siguiente "
    "operación en su cuenta:\n"
    "\n"
    "  Operación:          {operacion}\n"
    "  Instrumento:        {instrumento}\n"
    "  Cantidad:           {cantidad}\n"
    "  Precio unitario:    {precio}\n"
    "  Monto total:        {monto}\n"
    "  Moneda:             {moneda}\n"
    "  Estado:             {estado}\n"
    "\n"
    "  Cuenta comitente:   {cuenta_comitente}\n"
    "  Cuenta cotapartista:{cuenta_cotapartista}\n"
    "\n"
    "Ante cualquier consulta o aclaración, no dude en comunicarse con nosotros.\n"
    "\n"
    "Atentamente,\n"
    "{asesor}"
)


@dataclass
class ConfigDJData:
    id: int | None = None
    nombre: str = "DJ General"
    activa: bool = False
    incluir_texto_en_minuta: bool = False
    texto_alerta: str = ""
    reglas: list = field(default_factory=list)
    logica: str = "OR"
    activar_si_requiere_conformidad: bool = True


@dataclass
class ConfigFiltrosData:
    reglas: list = field(default_factory=list)
    logica: str = "OR"


def load_plantilla(db: Session) -> str:
    row = db.get(Plantilla, 1)
    return row.texto if row else DEFAULT_PLANTILLA


def save_plantilla(db: Session, texto: str) -> None:
    now = datetime.now(timezone.utc)
    row = db.get(Plantilla, 1)
    if row:
        row.texto = texto
        row.actualizado_en = now
    else:
        db.add(Plantilla(id=1, texto=texto, actualizado_en=now))
    db.commit()


