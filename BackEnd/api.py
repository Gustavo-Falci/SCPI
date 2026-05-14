import asyncio
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from core.errors import rate_limit_handler
from core.limiter import limiter
from infra import migrations as _migrations
from infra.aws_clientes import rekognition_client, s3_client
from infra.database import close_pool
from services.agendador import iniciar_agendador
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

_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)


def _make_rotating_handler(filename: str) -> TimedRotatingFileHandler:
    h = TimedRotatingFileHandler(
        os.path.join(_LOG_DIR, filename),
        when="midnight",
        backupCount=90,
        encoding="utf-8",
    )
    h.setFormatter(logging.Formatter(_LOG_FORMAT))
    return h


# Console handler para desenvolvimento
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))

# Configurar root logger (console) + loggers específicos (arquivo)
logging.basicConfig(level=logging.INFO, handlers=[_console_handler])

logging.getLogger("scpi").addHandler(_make_rotating_handler("scpi.log"))
_audit_logger = logging.getLogger("scpi.audit")
_audit_logger.addHandler(_make_rotating_handler("scpi_audit.log"))
_audit_logger.propagate = False  # audit events must not duplicate into scpi.log

logger = logging.getLogger("scpi.api")


def _check_aws_connectivity():
    try:
        if rekognition_client:
            rekognition_client.list_collections(MaxResults=1)
            logger.info("AWS Rekognition: conectado.")
        else:
            logger.warning("AWS Rekognition: cliente não inicializado.")
    except Exception as e:
        logger.warning("AWS Rekognition: falha na verificação de conectividade: %s", e)
    try:
        if s3_client:
            s3_client.list_buckets()
            logger.info("AWS S3: conectado.")
        else:
            logger.warning("AWS S3: cliente não inicializado.")
    except Exception as e:
        logger.warning("AWS S3: falha na verificação de conectividade: %s", e)

app = FastAPI(title="SCPI API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

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

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1"])


_agendador_task: asyncio.Task | None = None


@app.on_event("startup")
async def _on_startup():
    global _agendador_task
    _migrations.run_all()
    _agendador_task = asyncio.create_task(iniciar_agendador())
    _check_aws_connectivity()


@app.on_event("shutdown")
async def _on_shutdown():
    global _agendador_task
    if _agendador_task:
        _agendador_task.cancel()
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
