"""A6 — a chamada precisa pertencer à sala do token.

Sem isso, o token da Sala 101 marca presença numa chamada da Sala 202: era o
furo que sobrava mesmo depois de a chamada virar explícita no payload.
"""
import asyncio

import pytest
from fastapi import BackgroundTasks, HTTPException


def _registrar(payload, sala, background_tasks=None):
    from routers.chamadas import registrar_presenca_camera

    return asyncio.run(
        registrar_presenca_camera(
            payload=payload,
            background_tasks=background_tasks or BackgroundTasks(),
            sala=sala,
        )
    )


def test_chamada_de_outra_sala_e_403(monkeypatch):
    import routers.chamadas as chamadas
    from routers.chamadas import PresencaCameraPayload

    registrou = []
    monkeypatch.setattr(
        chamadas, "obter_chamada_aberta_por_sala",
        lambda sala: {"chamada_id": 10} if sala == "Sala 101" else None,
    )
    monkeypatch.setattr(
        chamadas, "registrar_presenca_por_face",
        lambda *a, **k: registrou.append(a) or {"status": "ok"},
    )

    payload = PresencaCameraPayload(
        external_image_id="6f3a1c2e-8b44-4d19-9e77-2a5c0d1b4f83", chamada_id=99
    )

    with pytest.raises(HTTPException) as exc:
        _registrar(payload, sala="Sala 101")

    assert exc.value.status_code == 403
    assert registrou == []  # não chegou a tocar no fluxo de presença


def test_chamada_da_propria_sala_passa(monkeypatch):
    import routers.chamadas as chamadas
    from routers.chamadas import PresencaCameraPayload

    monkeypatch.setattr(
        chamadas, "obter_chamada_aberta_por_sala", lambda _s: {"chamada_id": 10}
    )
    monkeypatch.setattr(
        chamadas, "registrar_presenca_por_face",
        lambda *a, **k: {"motivo": None, "usuario_id": "z", "aluno_nome": "Y", "aluno_email": "y@x.com", "turma_nome": "Turma X"},
    )

    payload = PresencaCameraPayload(
        external_image_id="6f3a1c2e-8b44-4d19-9e77-2a5c0d1b4f83", chamada_id=10
    )

    resultado = _registrar(payload, sala="Sala 101")

    assert resultado is not None


def test_rota_aberta_sala_nao_tem_mais_path_param():
    """A sala vem do token, não do cliente: com path param, o .env da câmera
    podia divergir do token emitido."""
    from routers.chamadas import router

    caminhos = {rota.path for rota in router.routes}

    assert "/chamadas/aberta/sala" in caminhos
    assert "/chamadas/aberta/sala/{sala}" not in caminhos


def test_banco_indisponivel_no_guard_de_sala_e_503_nao_403(monkeypatch):
    """Achar do review pós-A6: se `obter_chamada_aberta_por_sala` não consegue
    falar com o banco, o guard de escopo de sala não pode responder 403 —
    isso é recusa definitiva para a câmera (`definitivo = status < 500`) e
    derrubaria a turma inteira em silêncio por causa de um blip de banco."""
    import routers.chamadas as chamadas
    from infra.database import DB_INDISPONIVEL
    from routers.chamadas import PresencaCameraPayload

    registrou = []
    monkeypatch.setattr(
        chamadas, "obter_chamada_aberta_por_sala", lambda _s: DB_INDISPONIVEL
    )
    monkeypatch.setattr(
        chamadas, "registrar_presenca_por_face",
        lambda *a, **k: registrou.append(a) or {"status": "ok"},
    )

    payload = PresencaCameraPayload(
        external_image_id="6f3a1c2e-8b44-4d19-9e77-2a5c0d1b4f83", chamada_id=99
    )

    with pytest.raises(HTTPException) as exc:
        _registrar(payload, sala="Sala 101")

    assert exc.value.status_code == 503
    assert registrou == []  # não chegou a tocar no fluxo de presença


def test_get_aberta_sala_banco_indisponivel_e_503(monkeypatch):
    """Mesmo guard, na rota GET usada pela câmera para descobrir a chamada:
    sem isso ela receberia `{"chamada_id": None}` (200) durante um blip e
    concluiria "sem chamada aberta" em vez de "tente de novo"."""
    import routers.chamadas as chamadas
    from infra.database import DB_INDISPONIVEL

    monkeypatch.setattr(
        chamadas, "obter_chamada_aberta_por_sala", lambda _s: DB_INDISPONIVEL
    )

    with pytest.raises(HTTPException) as exc:
        chamadas.chamada_aberta_por_sala(sala="Sala 101")

    assert exc.value.status_code == 503


def test_obter_chamada_aberta_por_sala_devolve_sentinela_quando_cursor_indisponivel(
    monkeypatch,
):
    """Nível de repositório: confirma que é a própria função quem já devolve
    a sentinela, sem depender do mock nos testes de rota acima."""
    from contextlib import contextmanager

    import repositories.chamadas as chamadas_repo
    from infra.database import DB_INDISPONIVEL

    @contextmanager
    def _cursor_indisponivel():
        yield None

    monkeypatch.setattr(chamadas_repo, "get_db_cursor", _cursor_indisponivel)

    assert chamadas_repo.obter_chamada_aberta_por_sala("Sala 101") is DB_INDISPONIVEL
