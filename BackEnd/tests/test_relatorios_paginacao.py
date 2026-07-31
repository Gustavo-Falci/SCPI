"""Envelope de paginação opt-in em /professor/relatorios/chamadas (sem DB)."""
from fastapi.responses import Response

from routers.relatorios import listar_relatorios_professor

USER = {"sub": "u1", "role": "Professor"}


def _preparar(monkeypatch, itens, total=100):
    monkeypatch.setattr("routers.relatorios.obter_professor_id", lambda _: "p1")
    monkeypatch.setattr("routers.relatorios.listar_relatorios", lambda **kw: itens)
    monkeypatch.setattr("routers.relatorios.contar_relatorios", lambda **kw: total)


def _itens(n):
    return [{"chamada_id": i} for i in range(n)]


def test_sem_paginado_devolve_array_puro(monkeypatch):
    # Protege a build antiga do app: ela faz Array.isArray(data) e renderiza
    # lista vazia se receber objeto — falha silenciosa, pior que erro.
    _preparar(monkeypatch, _itens(3))
    resp = listar_relatorios_professor(current_user=USER)
    assert isinstance(resp, list)
    assert len(resp) == 3


def test_paginado_devolve_envelope(monkeypatch):
    _preparar(monkeypatch, _itens(20), total=123)
    resp = listar_relatorios_professor(paginado=True, limit=20, offset=0, current_user=USER)
    assert resp["total"] == 123
    assert len(resp["items"]) == 20
    assert resp["has_more"] is True


def test_has_more_false_na_ultima_pagina(monkeypatch):
    _preparar(monkeypatch, _itens(3), total=23)
    resp = listar_relatorios_professor(paginado=True, limit=20, offset=20, current_user=USER)
    assert resp["has_more"] is False


def test_has_more_false_quando_cabe_tudo_na_primeira(monkeypatch):
    _preparar(monkeypatch, _itens(5), total=5)
    resp = listar_relatorios_professor(paginado=True, limit=20, offset=0, current_user=USER)
    assert resp["has_more"] is False


def test_limit_e_offset_chegam_no_servico(monkeypatch):
    capturado = {}
    monkeypatch.setattr("routers.relatorios.obter_professor_id", lambda _: "p1")
    monkeypatch.setattr("routers.relatorios.contar_relatorios", lambda **kw: 0)

    def fake_listar(**kw):
        capturado.update(kw)
        return []

    monkeypatch.setattr("routers.relatorios.listar_relatorios", fake_listar)
    listar_relatorios_professor(paginado=True, limit=20, offset=40, current_user=USER)
    assert capturado["limit"] == 20
    assert capturado["offset"] == 40


def test_pdf_vence_paginado(monkeypatch):
    # O PDF é o documento do recorte inteiro; paginar dentro dele perderia
    # linhas sem o leitor perceber.
    _preparar(monkeypatch, _itens(2))
    resp = listar_relatorios_professor(paginado=True, formato="pdf", current_user=USER)
    assert isinstance(resp, Response)


def test_contagem_recebe_os_mesmos_filtros(monkeypatch):
    capturado = {}
    monkeypatch.setattr("routers.relatorios.obter_professor_id", lambda _: "p1")
    monkeypatch.setattr("routers.relatorios.listar_relatorios", lambda **kw: [])

    def fake_contar(**kw):
        capturado.update(kw)
        return 0

    monkeypatch.setattr("routers.relatorios.contar_relatorios", fake_contar)
    listar_relatorios_professor(
        paginado=True, turma_id="t1", turno="Matutino", semestre="3", current_user=USER,
    )
    assert capturado["turma_id"] == "t1"
    assert capturado["turno"] == "Matutino"
    assert capturado["semestre"] == "3"
    assert capturado["professor_id"] == "p1"


def test_sem_paginado_nao_conta(monkeypatch):
    # COUNT extra a cada request do app antigo seria desperdício puro.
    chamou = []
    monkeypatch.setattr("routers.relatorios.obter_professor_id", lambda _: "p1")
    monkeypatch.setattr("routers.relatorios.listar_relatorios", lambda **kw: [])
    monkeypatch.setattr("routers.relatorios.contar_relatorios",
                        lambda **kw: chamou.append(1) or 0)
    listar_relatorios_professor(current_user=USER)
    assert chamou == []
