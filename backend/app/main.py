from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth
from app.core.dependencies import get_current_user
from app.schemas.order import DashboardPage

app = FastAPI(title="Gestión de Órdenes Bursátiles", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


# Stub routes so conftest auth_headers fixture can test protected endpoints.
# Task 9 will replace these with the real dashboard router.
@app.get("/dashboard/borradores", response_model=DashboardPage)
def stub_borradores(_=Depends(get_current_user)):
    return DashboardPage(items=[], total=0, page=1, size=50)


@app.get("/health")
def health():
    return {"status": "ok"}
