import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.limiter import limiter
from app.core.logging_config import setup_logging, RequestLoggingMiddleware
from app.routers import auth, plantilla, maestro
from app.services import imap_watcher

setup_logging()
_logger = logging.getLogger("mails_nico")


def _run_migrations():
    try:
        from alembic.config import Config
        from alembic import command
        import os
        alembic_ini = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
        if os.path.exists(alembic_ini):
            alembic_cfg = Config(alembic_ini)
            alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
            command.upgrade(alembic_cfg, "head")
            _logger.info("Migraciones aplicadas correctamente")
    except Exception as e:
        _logger.error("Error al aplicar migraciones: %s", e)


_run_migrations()

app = FastAPI(title="Sistema de Cobro por Mail", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response: StarletteResponse = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth.router)
app.include_router(plantilla.router)
app.include_router(maestro.router)


@app.on_event("startup")
async def startup():
    asyncio.create_task(imap_watcher.run_forever())
    _logger.info("IMAP watcher iniciado")


@app.get("/health")
def health():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "database": "ok"}
    except Exception:
        return {"status": "degraded", "database": "error"}
