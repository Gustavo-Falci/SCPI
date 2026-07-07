import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.limiter import limiter
from infra.database import get_db_cursor

logger = logging.getLogger("scpi.health")

router = APIRouter()


@router.get("/")
def home():
    return {"mensagem": "API SCPI está rodando!"}


@router.get("/health")
@limiter.limit("30/minute")
def health(request: Request):
    """Healthcheck: valida a conexão com o Postgres.

    200 {"status": "ok", "database": "ok"} — SELECT 1 funcionou.
    503 {"status": "degraded", "database": "error"} — sem conexão ou erro.
    O detalhe do erro vai para o log, nunca para o response (anônimo não
    recebe informação interna).
    """
    try:
        with get_db_cursor() as cur:
            if cur is None:
                raise RuntimeError("sem conexão com o banco (cursor None)")
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as e:
        logger.error("Healthcheck falhou: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "error"},
        )
    return {"status": "ok", "database": "ok"}
