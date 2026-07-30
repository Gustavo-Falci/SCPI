"""Testes do endpoint público GET /politica-privacidade."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from core.config import POLITICA_PRIVACIDADE_VERSAO, POLITICA_PRIVACIDADE_VIGENCIA
from core.errors import ErrorCode, rate_limit_handler
from core.limiter import limiter


def _make_client():
    from routers import public

    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.include_router(public.router)
    return TestClient(app)


def test_devolve_versao_vigente_do_config():
    resp = _make_client().get("/politica-privacidade")
    assert resp.status_code == 200
    body = resp.json()
    assert body["versao"] == POLITICA_PRIVACIDADE_VERSAO
    assert body["data_vigencia"] == POLITICA_PRIVACIDADE_VIGENCIA
    assert "url" in body


def test_nao_exige_autenticacao():
    # Sem header Authorization — o app precisa ler a política antes do login.
    resp = _make_client().get("/politica-privacidade")
    assert resp.status_code == 200


def test_error_code_politica_desatualizada_existe():
    from core.errors import DEFAULT_MESSAGES

    assert ErrorCode.POLITICA_DESATUALIZADA == "POLITICA_DESATUALIZADA"
    assert DEFAULT_MESSAGES[ErrorCode.POLITICA_DESATUALIZADA]
