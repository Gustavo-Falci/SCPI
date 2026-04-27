import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.limiter import limiter
from infra import migrations as _migrations
from infra.database import close_pool
from routers import (
    admin,
    alunos,
    auth,
    chamadas,
    notificacoes,
    professores,
    public,
    relatorios,
    turmas,
)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("scpi.api")

app = FastAPI(title="SCPI API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if _raw_origins:
    _allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    _allowed_origins = [
        "http://localhost:8081",
        "http://localhost:19006",
        "http://localhost:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def _on_startup():
    _migrations.run_all()


@app.on_event("shutdown")
def _on_shutdown():
    close_pool()


app.include_router(public.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(notificacoes.router)
app.include_router(alunos.router)
app.include_router(professores.router)
app.include_router(turmas.router)
app.include_router(chamadas.router)
app.include_router(relatorios.router)
