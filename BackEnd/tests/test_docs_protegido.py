"""Testes das rotas de documentação (/docs, /redoc, /openapi.json) protegidas.

Em produção o Swagger fica atrás de sessão de Admin e responde 404 para todo o
resto — 404, e não 401/403, para não confirmar a existência da rota a quem
varre a API. Fora de produção as três abrem sem autenticação, para não pedir
login no ambiente de desenvolvimento.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.auth_utils import ACCESS_COOKIE_NAME, create_access_token
from core.docs_protegidos import registrar_rotas_docs


def _make_client(producao: bool):
    """App mínimo com as rotas de docs (não importa api.py)."""
    app = FastAPI(
        title="SCPI API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    registrar_rotas_docs(app, producao=producao)
    return TestClient(app)


def _cookie_de(role: str) -> dict:
    token = create_access_token({"sub": "11111111-1111-1111-1111-111111111111", "role": role})
    return {ACCESS_COOKIE_NAME: token}


def test_producao_sem_sessao_devolve_404():
    resp = _make_client(producao=True).get("/docs")
    assert resp.status_code == 404


def test_producao_com_cookie_de_admin_abre_o_swagger():
    client = _make_client(producao=True)
    client.cookies.update(_cookie_de("Admin"))
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "swagger-ui" in resp.text


def test_producao_com_cookie_de_aluno_devolve_404():
    client = _make_client(producao=True)
    client.cookies.update(_cookie_de("Aluno"))
    assert client.get("/docs").status_code == 404


def test_producao_com_cookie_de_professor_devolve_404():
    client = _make_client(producao=True)
    client.cookies.update(_cookie_de("Professor"))
    assert client.get("/docs").status_code == 404


def test_producao_com_token_adulterado_devolve_404():
    client = _make_client(producao=True)
    client.cookies.update({ACCESS_COOKIE_NAME: "nao.e.um.jwt"})
    assert client.get("/docs").status_code == 404


def test_openapi_json_tem_o_mesmo_gate_que_a_pagina():
    """Sem isso, protege-se a página e deixa-se o spec aberto — o erro clássico."""
    client = _make_client(producao=True)
    assert client.get("/openapi.json").status_code == 404

    client.cookies.update(_cookie_de("Admin"))
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"] == "SCPI API"


def test_redoc_tem_o_mesmo_gate_que_a_pagina():
    client = _make_client(producao=True)
    assert client.get("/redoc").status_code == 404

    client.cookies.update(_cookie_de("Admin"))
    assert client.get("/redoc").status_code == 200


def test_bearer_de_admin_tambem_autoriza():
    """O app mobile e o curl usam Authorization: Bearer, não o cookie do portal."""
    token = create_access_token({"sub": "1", "role": "Admin"})
    resp = _make_client(producao=True).get(
        "/docs", headers={"Authorization": "Bearer %s" % token}
    )
    assert resp.status_code == 200


def test_fora_de_producao_abre_sem_autenticacao():
    client = _make_client(producao=False)
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_api_desliga_as_rotas_nativas_e_registra_as_protegidas():
    """Wiring: se `api.py` deixar docs_url ligado, a rota nativa (sem gate) vence."""
    import api

    assert api.app.docs_url is None
    assert api.app.redoc_url is None
    assert api.app.openapi_url is None

    caminhos = {r.path for r in api.app.routes}
    assert {"/docs", "/redoc", "/openapi.json"} <= caminhos
