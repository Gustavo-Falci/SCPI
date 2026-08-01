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
