"""Revogação de biometria grava evento na trilha (sem DB nem AWS)."""
from unittest.mock import MagicMock

import pytest

from routers.alunos import revogar_biometria


class _RequestFake:
    def __init__(self, ip="203.0.113.7", ua="Expo/1.0"):
        self.client = MagicMock(host=ip)
        self.headers = {"user-agent": ua}


def _preparar(monkeypatch):
    """Neutraliza AWS e DB, devolve a lista de eventos registrados."""
    eventos = []
    monkeypatch.setattr("routers.alunos.buscar_aluno_por_usuario_id",
                        lambda _: {"aluno_id": "aluno-1"})
    monkeypatch.setattr("routers.alunos.listar_rostos_ativos_por_aluno",
                        lambda _: [{"face_id_rekognition": "f1",
                                    "s3_path_cadastro": "alunos/x.jpg",
                                    "angulo": "frontal"}])
    monkeypatch.setattr("routers.alunos.deletar_rosto", lambda _: None)
    monkeypatch.setattr("routers.alunos.s3_client", MagicMock())
    monkeypatch.setattr("routers.alunos.revogar_rosto_por_aluno", lambda _: 1)
    monkeypatch.setattr("routers.alunos.registrar_evento",
                        lambda *a, **k: eventos.append((a, k)) or True)
    return eventos


def test_revogacao_pelo_titular_marca_origem_app(monkeypatch):
    eventos = _preparar(monkeypatch)
    revogar_biometria("u1", request=_RequestFake(),
                      current_user={"sub": "u1", "role": "Aluno"})
    args, kwargs = eventos[0]
    assert args[1] == "revogacao"
    assert kwargs["origem"] == "app"
    assert kwargs["ip"] == "203.0.113.7"


def test_revogacao_pelo_admin_marca_origem_admin(monkeypatch):
    eventos = _preparar(monkeypatch)
    revogar_biometria("u1", request=_RequestFake(),
                      current_user={"sub": "admin-9", "role": "Admin"})
    assert eventos[0][1]["origem"] == "admin"


def test_revogacao_registra_versao_vigente(monkeypatch):
    from core.config import POLITICA_PRIVACIDADE_VERSAO

    eventos = _preparar(monkeypatch)
    revogar_biometria("u1", request=_RequestFake(),
                      current_user={"sub": "u1", "role": "Aluno"})
    assert eventos[0][0][2] == POLITICA_PRIVACIDADE_VERSAO


def test_sem_biometria_ativa_nao_registra_evento(monkeypatch):
    from fastapi import HTTPException

    eventos = _preparar(monkeypatch)
    monkeypatch.setattr("routers.alunos.listar_rostos_ativos_por_aluno", lambda _: [])
    with pytest.raises(HTTPException):
        revogar_biometria("u1", request=_RequestFake(),
                          current_user={"sub": "u1", "role": "Aluno"})
    assert eventos == []
