"""Identidade biométrica derivada do aluno_id, não do nome (sem DB).

O nome normalizado colidia entre homônimos: dois "João da Silva" geravam o
mesmo ExternalImageId e a presença caía no aluno errado.
"""
import asyncio
import uuid
from unittest.mock import MagicMock

import pytest

import routers.alunos as mod


def _cadastrar(monkeypatch, nome, aluno_id, usuario_id):
    """Chama cadastrar_aluno_api com AWS e banco mockados.

    Devolve o mock de upsert_rosto para inspeção dos argumentos gravados.
    """
    upsert = MagicMock()

    # O endpoint é decorado com @limiter.limit, que exige um Request real do
    # Starlette quando habilitado (checagem no próprio slowapi, antes do corpo
    # da função rodar). Chamando a função diretamente (sem passar pelo ASGI/
    # TestClient) não há esse Request; desligar o limiter aqui é o jeito mais
    # simples de exercitar só a lógica de identidade que este teste cobre.
    monkeypatch.setattr(mod.limiter, "enabled", False)

    async def _valida(_foto):
        return b"\xff\xd8\xff-bytes-de-jpeg"

    monkeypatch.setattr(mod, "validate_image_upload", _valida)
    monkeypatch.setattr(mod, "s3_client", MagicMock())
    monkeypatch.setattr(
        mod, "indexar_rosto_da_imagem_s3",
        lambda *a, **k: {"FaceRecords": [{"Face": {"FaceId": "face-1"}}]},
    )
    monkeypatch.setattr(
        mod, "buscar_usuario_id_por_id", lambda _uid: {"usuario_id": usuario_id}
    )
    monkeypatch.setattr(
        mod, "buscar_aluno_por_usuario_id", lambda _uid: {"aluno_id": aluno_id}
    )
    monkeypatch.setattr(mod, "obter_rosto_por_angulo", lambda *a: None)
    monkeypatch.setattr(mod, "upsert_rosto", upsert)
    monkeypatch.setattr(mod, "registrar_aceite_se_novo", lambda *a, **k: True)
    monkeypatch.setattr(mod, "validar_consentimento", lambda *a, **k: None)

    foto = MagicMock()
    foto.content_type = "image/jpeg"

    asyncio.run(
        mod.cadastrar_aluno_api(
            request=None,
            user_id=usuario_id,
            nome=nome,
            email="aluno@teste.local",
            ra="RA1234",
            foto=foto,
            consentimento_biometrico=True,
            politica_versao="1.0",
            angulo="frontal",
            current_user={"sub": usuario_id, "role": "Aluno"},
        )
    )
    return upsert


def test_external_id_e_o_aluno_id(monkeypatch):
    aluno_id = str(uuid.uuid4())
    usuario_id = str(uuid.uuid4())

    upsert = _cadastrar(monkeypatch, "João da Silva", aluno_id, usuario_id)

    _aluno, external_id, _face, _filename, _angulo = upsert.call_args[0]
    assert external_id == aluno_id


def test_homonimos_recebem_ids_distintos(monkeypatch):
    """O teste que o sistema não tinha."""
    id_a, id_b = str(uuid.uuid4()), str(uuid.uuid4())

    upsert_a = _cadastrar(monkeypatch, "João da Silva", id_a, str(uuid.uuid4()))
    upsert_b = _cadastrar(monkeypatch, "João da Silva", id_b, str(uuid.uuid4()))

    assert upsert_a.call_args[0][1] != upsert_b.call_args[0][1]


def test_chave_s3_nao_contem_o_nome(monkeypatch):
    aluno_id = str(uuid.uuid4())

    upsert = _cadastrar(monkeypatch, "João da Silva", aluno_id, str(uuid.uuid4()))

    filename = upsert.call_args[0][3]
    assert filename.startswith(f"alunos/{aluno_id}/")
    assert "Joao" not in filename
    assert "Silva" not in filename


def test_core_utils_foi_removido():
    """formatar_nome_para_external_id não deve sobreviver ao corte."""
    with pytest.raises(ImportError):
        from core.utils import formatar_nome_para_external_id  # noqa: F401
