"""Testes da rota GET /admin/alunos — repositório mockado."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """TestClient autenticado como Admin.

    O router /admin inteiro exige require_role("Admin"), que por sua vez depende
    de get_current_user — sobrescrever essa dependência é o ponto de entrada para
    testar as rotas sem emitir JWT de verdade.
    """
    from api import app
    from core.security import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"sub": "admin@teste.local", "role": "Admin"}
    yield TestClient(app)
    app.dependency_overrides.clear()


def _patches(items=None, total=0, ocultos=0):
    return (
        patch("routers.admin.listar_alunos_para_admin",
              return_value={"items": items or [], "total": total}),
        patch("routers.admin.contar_alunos_pendentes", return_value=ocultos),
    )


def test_sem_params_devolve_envelope(client):
    p_lista, p_contar = _patches(items=[{"aluno_id": "a1", "nome": "Maria"}], total=1)
    with p_lista as m_lista, p_contar:
        r = client.get("/admin/alunos")
    assert r.status_code == 200
    assert r.json() == {"items": [{"aluno_id": "a1", "nome": "Maria"}],
                        "total": 1, "ocultos_pendentes": 0}
    assert m_lista.call_args.kwargs["page"] == 1
    assert m_lista.call_args.kwargs["limit"] == 10


def test_params_chegam_ao_repositorio(client):
    p_lista, p_contar = _patches()
    with p_lista as m_lista, p_contar:
        client.get("/admin/alunos?q=maria&turno=Noturno&semestre=3"
                   "&periodo_letivo=2026/1&situacao=sem_turma&page=2&limit=25")
    kwargs = m_lista.call_args.kwargs
    assert kwargs["q"] == "maria"
    assert kwargs["turno"] == "Noturno"
    assert kwargs["semestre"] == "3"
    assert kwargs["periodo_letivo"] == "2026/1"
    assert kwargs["situacao"] == "sem_turma"
    assert kwargs["page"] == 2
    assert kwargs["limit"] == 25


def test_limit_acima_do_teto_e_reduzido_a_100(client):
    p_lista, p_contar = _patches()
    with p_lista as m_lista, p_contar:
        r = client.get("/admin/alunos?limit=5000")
    assert r.status_code == 200
    assert m_lista.call_args.kwargs["limit"] == 100


def test_turno_invalido_rejeitado(client):
    r = client.get("/admin/alunos?turno=Vespertino")
    assert r.status_code == 422


def test_situacao_invalida_rejeitada(client):
    r = client.get("/admin/alunos?situacao=qualquer_coisa")
    assert r.status_code == 422


def test_page_zero_rejeitada(client):
    r = client.get("/admin/alunos?page=0")
    assert r.status_code == 422


def test_ocultos_recebe_os_mesmos_filtros_de_escopo(client):
    p_lista, p_contar = _patches(ocultos=42)
    with p_lista, p_contar as m_contar:
        r = client.get("/admin/alunos?turno=Matutino&semestre=3&q=ana")
    assert r.json()["ocultos_pendentes"] == 42
    kwargs = m_contar.call_args.kwargs
    assert kwargs["turno"] == "Matutino"
    assert kwargs["semestre"] == "3"
    assert kwargs["q"] == "ana"


def test_situacao_pendentes_nao_conta_ocultos(client):
    """A lista JÁ é a dos pendentes; o banner não faz sentido nela."""
    p_lista, p_contar = _patches(ocultos=42)
    with p_lista, p_contar as m_contar:
        r = client.get("/admin/alunos?situacao=pendentes&turno=Matutino")
    assert r.json()["ocultos_pendentes"] == 0
    m_contar.assert_not_called()
