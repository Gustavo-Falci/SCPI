"""Contrato do endpoint da câmera (sem DB).

A câmera é a única consumidora, e ela precisa distinguir recusa definitiva
(não adianta repetir nesta chamada) de falha transitória (tentar de novo).
"""
import asyncio

import pytest
from fastapi import HTTPException
from pydantic import ValidationError


def _chamar(payload, background_tasks=None):
    from routers.chamadas import registrar_presenca_camera
    from fastapi import BackgroundTasks

    return asyncio.run(
        registrar_presenca_camera(
            payload=payload,
            background_tasks=background_tasks or BackgroundTasks(),
            _=None,
        )
    )


def test_payload_exige_chamada_id():
    from routers.chamadas import PresencaCameraPayload

    with pytest.raises(ValidationError):
        PresencaCameraPayload(external_image_id="6f3a1c2e-8b44-4d19-9e77-2a5c0d1b4f83")


def test_endpoint_selfie_nao_existe_mais():
    """O fluxo órfão de presença por selfie permitia a qualquer Aluno
    autenticado marcar a própria presença de qualquer lugar, sem liveness."""
    from routers.chamadas import router

    caminhos = {rota.path for rota in router.routes}
    assert "/chamadas/registrar_rosto" not in caminhos


def test_sucesso_responde_200_e_agenda_notificacao_com_argumentos_na_ordem(monkeypatch):
    """Afirma o wiring da notificação, não só o status.

    A assinatura é enviar_notificacoes_presenca(usuario_id, aluno_nome,
    aluno_email, turma_nome): trocar nome e e-mail de lugar mandaria o e-mail
    para lugar nenhum e imprimiria o endereço no corpo da mensagem, sem nenhum
    sinal — o BackgroundTask engole o resultado e o endpoint continua 200.
    """
    from fastapi import BackgroundTasks

    from routers.chamadas import PresencaCameraPayload
    import routers.chamadas as mod
    from services.notificacoes import enviar_notificacoes_presenca

    monkeypatch.setattr(
        mod,
        "registrar_presenca_por_face",
        lambda eid, cid: {
            "motivo": None, "usuario_id": "u1", "aluno_nome": "Ana",
            "aluno_email": "ana@x.com", "turma_nome": "Cálculo I",
        },
    )
    background_tasks = BackgroundTasks()

    resp = _chamar(
        PresencaCameraPayload(external_image_id="x", chamada_id=1),
        background_tasks=background_tasks,
    )

    assert resp["ja_registrado"] is False
    assert len(background_tasks.tasks) == 1
    tarefa = background_tasks.tasks[0]
    assert tarefa.func is enviar_notificacoes_presenca
    assert tarefa.args == ("u1", "Ana", "ana@x.com", "Cálculo I")


def test_ja_registrado_responde_200_idempotente(monkeypatch):
    from routers.chamadas import PresencaCameraPayload
    import routers.chamadas as mod
    from repositories.usuarios import MOTIVO_JA_REGISTRADO

    monkeypatch.setattr(
        mod, "registrar_presenca_por_face",
        lambda eid, cid: {"motivo": MOTIVO_JA_REGISTRADO},
    )
    resp = _chamar(PresencaCameraPayload(external_image_id="x", chamada_id=1))
    assert resp["ja_registrado"] is True


@pytest.mark.parametrize(
    "motivo_attr, status",
    [
        ("MOTIVO_ROSTO_DESCONHECIDO", 404),
        ("MOTIVO_CHAMADA_FECHADA", 409),
        ("MOTIVO_NAO_MATRICULADO", 403),
        ("MOTIVO_ERRO_INTERNO", 503),
    ],
)
def test_recusa_mapeia_para_status_e_error_code(monkeypatch, motivo_attr, status):
    from routers.chamadas import PresencaCameraPayload
    import routers.chamadas as mod
    import repositories.usuarios as repo

    motivo = getattr(repo, motivo_attr)
    monkeypatch.setattr(
        mod, "registrar_presenca_por_face", lambda eid, cid: {"motivo": motivo}
    )

    with pytest.raises(HTTPException) as exc:
        _chamar(PresencaCameraPayload(external_image_id="x", chamada_id=1))

    assert exc.value.status_code == status
    assert exc.value.detail["error_code"] == motivo
