import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.config import (
    POLITICA_PRIVACIDADE_VERSAO,
    POLITICA_PRIVACIDADE_VIGENCIA,
    SCPI_PRIVACY_URL,
)
from core.limiter import limiter
from infra.database import get_db_cursor
from schemas.respostas.public import ApiNoAr, PoliticaPrivacidadeVigente, SaudeDaApi

logger = logging.getLogger("scpi.health")

router = APIRouter(tags=["público"])


@router.get(
    "/",
    summary="Confirma que a API está no ar",
    responses={200: {"model": ApiNoAr}},
)
def home():
    """Endpoint raiz, sem autenticação: confirma que a API está respondendo."""
    return {"mensagem": "API SCPI está rodando!"}


@router.get(
    "/politica-privacidade",
    summary="Versão vigente da política de privacidade",
    responses={200: {"model": PoliticaPrivacidadeVigente}},
)
@limiter.limit("30/minute")
def politica_privacidade(request: Request):
    """Versão vigente da política — público, o app lê antes de mostrar o aceite."""
    return {
        "versao": POLITICA_PRIVACIDADE_VERSAO,
        "data_vigencia": POLITICA_PRIVACIDADE_VIGENCIA,
        "url": SCPI_PRIVACY_URL,
    }


@router.get(
    "/health",
    summary="Healthcheck da API e do banco",
    # O 503 tem o mesmo formato do 200 e é resposta prevista, não erro genérico:
    # documentar só o 200 esconderia do leitor o corpo que o monitor recebe.
    responses={
        200: {"model": SaudeDaApi},
        503: {"model": SaudeDaApi, "description": "Banco indisponível"},
    },
)
@limiter.limit("30/minute")
def health(request: Request):
    """Healthcheck: valida a conexão com o Postgres.

    200 {"status": "ok", "database": "ok"} — SELECT 1 funcionou.
    503 {"status": "degraded", "database": "error"} — sem conexão ou erro.
    HEAD aceito porque o monitor free do UptimeRobot usa HEAD por padrão.
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


# HEAD em rota propria, e nao methods=["GET","HEAD"] no mesmo api_route: o
# api_route unico gera operationId duplicado no OpenAPI, o que quebra gerador
# de cliente. Fora do schema por ser o mesmo recurso do GET acima.
@router.head("/health", include_in_schema=False)
@limiter.limit("30/minute")
def health_head(request: Request):
    """Mesmo healthcheck do GET. O monitor free do UptimeRobot usa HEAD."""
    return health(request)
