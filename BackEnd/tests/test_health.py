"""Testes do endpoint GET /health (sem DB real)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from core.errors import rate_limit_handler
from core.limiter import limiter


def _make_client():
    """App mínimo: só o router público + limiter (não importa api.py)."""
    from routers import public

    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.include_router(public.router)
    return TestClient(app)


@contextmanager
def _cursor_ok():
    cur = MagicMock()
    cur.fetchone.return_value = {"?column?": 1}
    yield cur


@contextmanager
def _cursor_none():
    yield None


@contextmanager
def _cursor_explode():
    cur = MagicMock()
    cur.execute.side_effect = RuntimeError("connection reset")
    yield cur


def test_health_db_ok_retorna_200():
    with patch("routers.public.get_db_cursor", _cursor_ok):
        resp = _make_client().get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok"}


def test_health_sem_conexao_retorna_503():
    with patch("routers.public.get_db_cursor", _cursor_none):
        resp = _make_client().get("/health")
    assert resp.status_code == 503
    assert resp.json() == {"status": "degraded", "database": "error"}


def test_health_excecao_no_execute_retorna_503():
    with patch("routers.public.get_db_cursor", _cursor_explode):
        resp = _make_client().get("/health")
    assert resp.status_code == 503
    assert resp.json() == {"status": "degraded", "database": "error"}


def test_health_nao_vaza_detalhe_de_erro():
    with patch("routers.public.get_db_cursor", _cursor_explode):
        resp = _make_client().get("/health")
    assert "connection reset" not in resp.text


def test_health_aceita_head_db_ok():
    # UptimeRobot free usa HEAD por padrão — endpoint precisa responder 200.
    with patch("routers.public.get_db_cursor", _cursor_ok):
        resp = _make_client().head("/health")
    assert resp.status_code == 200


def test_health_head_db_fora_retorna_503():
    with patch("routers.public.get_db_cursor", _cursor_none):
        resp = _make_client().head("/health")
    assert resp.status_code == 503
