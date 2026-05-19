"""Mitigação CSRF para autenticação por cookie.

Estratégia: header customizado X-Requested-With em todas as mutações
(POST/PUT/PATCH/DELETE) quando o cookie scpi_access é a fonte de autenticação.

Por que funciona: browsers não permitem que <form> nem requests cross-origin
"simples" definam headers customizados sem disparar preflight CORS. Como a
política CORS já restringe origens, um atacante de origem terceira não consegue
forjar a requisição com o header.

Pulamos a checagem quando:
- Método é seguro (GET/HEAD/OPTIONS): mutação não acontece.
- Existe header Authorization: cliente mobile com Bearer; CSRF não aplica
  (cookies não são enviados ambientalmente nesse fluxo).
- Cookie scpi_access ausente: sem auth por cookie, sem alvo de CSRF.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from core.auth_utils import ACCESS_COOKIE_NAME

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_EXPECTED_HEADER_VALUE = "XMLHttpRequest"
# Endpoints isentos de CSRF: login não tem vetor útil (atacante precisa
# da senha para o request ter efeito) e refresh é protegido pelo SameSite=Strict
# do cookie scpi_refresh + posse do token opaco no body. Sem isenção, clientes
# mobile que reaproveitam o cookie scpi_access do jar nativo ficam travados.
_CSRF_EXEMPT_PATHS = {"/auth/login", "/auth/refresh"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        if request.url.path in _CSRF_EXEMPT_PATHS:
            return await call_next(request)

        if request.headers.get("authorization"):
            return await call_next(request)

        if not request.cookies.get(ACCESS_COOKIE_NAME):
            return await call_next(request)

        if request.headers.get("x-requested-with") != _EXPECTED_HEADER_VALUE:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": {
                        "detail": "Requisição rejeitada por proteção CSRF.",
                        "error_code": "CSRF_HEADER_MISSING",
                    }
                },
            )

        return await call_next(request)
