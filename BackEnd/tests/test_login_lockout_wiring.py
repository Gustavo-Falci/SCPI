from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from core.errors import rate_limit_handler
from core.limiter import limiter


def _client():
    from routers import auth

    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.include_router(auth.router)
    return TestClient(app)


def test_login_bloqueado_retorna_429():
    futuro = datetime.utcnow() + timedelta(minutes=10)
    with patch("routers.auth.esta_bloqueado", return_value=futuro):
        resp = _client().post(
            "/auth/login", data={"username": "x@x.com", "password": "seja-o-que-for"}
        )
    assert resp.status_code == 429


def test_login_falho_registra_falha():
    with patch("routers.auth.esta_bloqueado", return_value=None), \
         patch("routers.auth.buscar_usuario_login_por_email", return_value=None), \
         patch("routers.auth.registrar_falha") as spy:
        resp = _client().post(
            "/auth/login", data={"username": "x@x.com", "password": "errada"}
        )
    assert resp.status_code == 401
    spy.assert_called_once_with("x@x.com")


def test_login_ok_limpa_falhas():
    fake_user = {
        "usuario_id": "11111111-1111-1111-1111-111111111111",
        "email": "Y@x.com", "nome": "Y", "senha": "hash",
        "tipo_usuario": "Professor", "primeiro_acesso": False,
    }
    with patch("routers.auth.esta_bloqueado", return_value=None), \
         patch("routers.auth.buscar_usuario_login_por_email", return_value=fake_user), \
         patch("routers.auth.verify_password", return_value=True), \
         patch("routers.auth.inserir_refresh_token", return_value=True), \
         patch("routers.auth.limpar_falhas") as spy:
        resp = _client().post(
            "/auth/login", data={"username": "Y@x.com", "password": "certa"}
        )
    assert resp.status_code == 200
    spy.assert_called_once_with("y@x.com")  # email_key é lowercased
