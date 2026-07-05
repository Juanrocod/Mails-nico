import os
import re
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
    fecha_envio = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    cuerpo_renderizado = _render_cuerpo(envio, plantilla, fecha_envio)
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
        fecha_envio=fecha_envio,
        cuerpo_html=cuerpo_renderizado,
        nombre_empresa=plantilla.nombre_empresa,
        logo_url=plantilla.logo_url or "",
        color_primario=plantilla.color_primario,
        unsubscribe_url=unsubscribe_url,
    )
    html_inline = transform(html_raw)
    texto_plano = _generar_texto_plano(envio, plantilla, cuerpo_renderizado, fecha_envio, unsubscribe_url)

    msg = EmailMessage()
    msg["Subject"] = plantilla.asunto
    msg["To"] = envio.email
    if unsubscribe_url != "#":
        # RFC 2369 — señal de legitimidad que Gmail/Yahoo/Outlook buscan en el
        # header, no alcanza con el link de baja dentro del HTML del cuerpo.
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    msg.set_content(texto_plano)
    msg.add_alternative(html_inline, subtype="html")
    return msg


def _render_cuerpo(envio: EnvioParsed, plantilla: Plantilla, fecha_envio: str) -> str:
    variables = {
        "nombre": envio.nombre,
        "monto": f"{envio.monto:.2f}",
        "localidad": envio.localidad or "",
        "clave_union": envio.clave_union,
        "fecha_envio": fecha_envio,
    }
    result = plantilla.cuerpo_html
    for key, val in variables.items():
        result = result.replace(f"{{{{{key}}}}}", val)
    return result


def _html_a_texto(html: str) -> str:
    texto = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    texto = re.sub(r"</p>", "\n\n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _generar_texto_plano(
    envio: EnvioParsed,
    plantilla: Plantilla,
    cuerpo_renderizado: str,
    fecha_envio: str,
    unsubscribe_url: str,
) -> str:
    partes = [
        plantilla.nombre_empresa,
        "",
        _html_a_texto(cuerpo_renderizado),
        "",
        f"Monto adeudado: ${envio.monto:.2f}",
        f"Fecha de envío: {fecha_envio}",
        f"Referencia: {envio.clave_union}",
    ]
    if unsubscribe_url != "#":
        partes += ["", f"Si no desea recibir más comunicaciones, visite: {unsubscribe_url}"]
    return "\n".join(partes)
