import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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
from app.routers import auth, plantilla, maestro, ciclos, configuracion, unsubscribe
from app.services import imap_watcher

setup_logging()
_logger = logging.getLogger("mails_nico")


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

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(plantilla.router)
app.include_router(maestro.router)
app.include_router(ciclos.router)
app.include_router(configuracion.router)
app.include_router(unsubscribe.router)


# Run migrations manually before starting: alembic upgrade head
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
