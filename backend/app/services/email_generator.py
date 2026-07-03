import os
from datetime import datetime, timezone
from email.message import EmailMessage

from jinja2 import Environment, FileSystemLoader
from premailer import transform

from app.core.security import generate_unsubscribe_token
from app.models.plantilla import Plantilla
from app.services.excel_joiner import EnvioParsed

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR), autoescape=False)


def generate_email(
    envio: EnvioParsed,
    plantilla: Plantilla,
    unsubscribe_base_url: str = "",
) -> EmailMessage:
    cuerpo_renderizado = _render_cuerpo(envio, plantilla)
    if unsubscribe_base_url:
        token = generate_unsubscribe_token(envio.clave_union)
        unsubscribe_url = f"{unsubscribe_base_url}/unsubscribe/{token}"
    else:
        unsubscribe_url = "#"
    template = _jinja_env.get_template("mail_cobro.html")
    html_raw = template.render(
        nombre=envio.nombre,
        monto=f"{envio.monto:.2f}",
        localidad=envio.localidad or "",
        clave_union=envio.clave_union,
        fecha_envio=datetime.now(timezone.utc).strftime("%d/%m/%Y"),
        cuerpo_html=cuerpo_renderizado,
        nombre_empresa=plantilla.nombre_empresa,
        logo_url=plantilla.logo_url or "",
        color_primario=plantilla.color_primario,
        unsubscribe_url=unsubscribe_url,
    )
    html_inline = transform(html_raw)

    msg = EmailMessage()
    msg["Subject"] = plantilla.asunto
    msg["To"] = envio.email
    msg.set_content("Este mensaje requiere un cliente de correo con soporte HTML.")
    msg.add_alternative(html_inline, subtype="html")
    return msg


def _render_cuerpo(envio: EnvioParsed, plantilla: Plantilla) -> str:
    variables = {
        "nombre": envio.nombre,
        "monto": f"{envio.monto:.2f}",
        "localidad": envio.localidad or "",
        "clave_union": envio.clave_union,
        "fecha_envio": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
    }
    result = plantilla.cuerpo_html
    for key, val in variables.items():
        result = result.replace(f"{{{{{key}}}}}", val)
    return result
