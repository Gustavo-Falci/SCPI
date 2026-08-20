"""Rotas de documentação (/docs, /redoc, /openapi.json) atrás de sessão de Admin.

O FastAPI serve essas três rotas sozinho, mas sem gate nenhum: em produção isso
entrega o mapa completo da API a quem passar. Aqui elas são desligadas no
construtor do app e reabertas por estas rotas, que exigem Admin quando em
produção.

Quem não é Admin recebe **404**, não 401 nem 403: 404 não confirma que a
documentação existe naquele host. É o mesmo critério anti-enumeração já usado
em `require_self_or_admin`.

O token é extraído à mão, sem reusar `get_current_user`, porque aquela
dependency levanta 401 antes de o código desta rota rodar — e 401 é exatamente
a resposta que não queremos dar aqui.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse

from core.auth_utils import ACCESS_COOKIE_NAME, decode_access_token

_TEMA_ESCURO = Path(__file__).resolve().parent.parent / "static" / "swagger-tema-escuro.css"
_TEMA_ESCURO_URL = "/docs/tema-escuro.css"


def _token_da_requisicao(request: Request) -> str | None:
    """Bearer no header tem prioridade; cookie do portal é o fallback."""
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return request.cookies.get(ACCESS_COOKIE_NAME)


def _exigir_admin(request: Request, producao: bool) -> None:
    if not producao:
        return
    token = _token_da_requisicao(request)
    payload = decode_access_token(token) if token else None
    if not payload or payload.get("role") != "Admin":
        raise HTTPException(status_code=404, detail="Not Found")


def registrar_rotas_docs(app: FastAPI, producao: bool) -> None:
    """Registra /docs, /redoc e /openapi.json no app, com gate de Admin.

    O app precisa ter sido criado com `docs_url=None`, `redoc_url=None` e
    `openapi_url=None`, senão as rotas nativas (sem gate) respondem primeiro.
    """

    @app.get("/openapi.json", include_in_schema=False)
    def openapi_protegido(request: Request):
        _exigir_admin(request, producao)
        return JSONResponse(app.openapi())

    @app.get(_TEMA_ESCURO_URL, include_in_schema=False)
    def tema_escuro(request: Request):
        _exigir_admin(request, producao)
        return FileResponse(_TEMA_ESCURO, media_type="text/css")

    @app.get("/docs", include_in_schema=False)
    def swagger_protegido(request: Request):
        _exigir_admin(request, producao)
        # swagger_css_url substitui a folha base; o arquivo servido a reimporta.
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="%s — Swagger" % app.title,
            swagger_css_url=_TEMA_ESCURO_URL,
        )

    @app.get("/redoc", include_in_schema=False)
    def redoc_protegido(request: Request):
        _exigir_admin(request, producao)
        return get_redoc_html(openapi_url="/openapi.json", title="%s — ReDoc" % app.title)
