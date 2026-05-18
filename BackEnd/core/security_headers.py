"""Middleware que injeta cabeçalhos HTTP de segurança em todas as respostas.

Cobre os controles do manual §3.5:
- Strict-Transport-Security (apenas em produção, evita quebrar dev em HTTP)
- Content-Security-Policy (rígido para API; relaxado em /docs por causa do Swagger)
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy
"""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_IS_PRODUCTION = os.getenv("ENVIRONMENT", "").strip().lower() == "production"

_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}

_CSP_STRICT = (
    "default-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'none'"
)

_CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'"
)

_PERMISSIONS_POLICY = (
    "geolocation=(), microphone=(), camera=(), payment=(), usb=(), "
    "magnetometer=(), gyroscope=(), accelerometer=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        path = request.url.path

        # Remove fingerprint do servidor — atacante não precisa saber a stack.
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", _PERMISSIONS_POLICY)
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        if path in _DOCS_PATHS or path.startswith("/docs/") or path.startswith("/redoc/"):
            response.headers.setdefault("Content-Security-Policy", _CSP_DOCS)
        else:
            response.headers.setdefault("Content-Security-Policy", _CSP_STRICT)

        if _IS_PRODUCTION:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )

        return response
