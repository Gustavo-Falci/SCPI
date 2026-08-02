"""IO síncrono dos endpoints async roda fora do event loop (sem DB).

psycopg2 e boto3 são bloqueantes. Chamados no corpo de uma corrotina, param o
worker inteiro enquanto esperam rede: no caminho da câmera isso acontece a cada
rosto reconhecido — poucos segundos, por sala, aula inteira.

Os testes comparam a thread de execução com a do event loop. Trocar
`await run_in_threadpool(f, ...)` por `f(...)` faz os dois falharem.
"""
import asyncio
import threading
import uuid
from unittest.mock import MagicMock


def test_camera_nao_bloqueia_event_loop(monkeypatch):
    from fastapi import BackgroundTasks

    import routers.chamadas as mod
    from routers.chamadas import PresencaCameraPayload

    threads = {}

    def _chamada_aberta(_sala):
        threads["obter_chamada"] = threading.get_ident()
        return {"chamada_id": 1}

    def _registrar(_eid, _cid):
        threads["registrar_presenca"] = threading.get_ident()
        return {"motivo": None}

    monkeypatch.setattr(mod, "obter_chamada_aberta_por_sala", _chamada_aberta)
    monkeypatch.setattr(mod, "registrar_presenca_por_face", _registrar)

    async def _executar():
        threads["loop"] = threading.get_ident()
        return await mod.registrar_presenca_camera(
            payload=PresencaCameraPayload(external_image_id="x", chamada_id=1),
            background_tasks=BackgroundTasks(),
            sala="Sala 101",
        )

    resposta = asyncio.run(_executar())

    assert resposta["ja_registrado"] is False
    assert threads["obter_chamada"] != threads["loop"], "query da sala rodou no event loop"
    assert threads["registrar_presenca"] != threads["loop"], "registro rodou no event loop"


def test_cadastro_face_nao_bloqueia_event_loop(monkeypatch):
    """S3 + Rekognition + 5 queries — o request mais pesado do app."""
    import routers.alunos as mod

    usuario_id = str(uuid.uuid4())
    threads = {}

    def _buscar_usuario(_uid):
        threads["persistir"] = threading.get_ident()
        return {"usuario_id": usuario_id}

    # Ver test_cadastro_face_external_id: chamada direta não passa pelo ASGI,
    # então o limiter fica sem o Request que ele exige.
    monkeypatch.setattr(mod.limiter, "enabled", False)

    async def _valida(_foto):
        return b"\xff\xd8\xff-bytes-de-jpeg"

    monkeypatch.setattr(mod, "validate_image_upload", _valida)
    monkeypatch.setattr(mod, "s3_client", MagicMock())
    monkeypatch.setattr(
        mod, "indexar_rosto_da_imagem_s3",
        lambda *a, **k: {"FaceRecords": [{"Face": {"FaceId": "face-1"}}]},
    )
    monkeypatch.setattr(mod, "buscar_usuario_id_por_id", _buscar_usuario)
    monkeypatch.setattr(
        mod, "buscar_aluno_por_usuario_id", lambda _uid: {"aluno_id": str(uuid.uuid4())}
    )
    monkeypatch.setattr(mod, "obter_rosto_por_angulo", lambda *a: None)
    monkeypatch.setattr(mod, "upsert_rosto", MagicMock())
    monkeypatch.setattr(mod, "registrar_aceite_se_novo", lambda *a, **k: True)
    monkeypatch.setattr(mod, "validar_consentimento", lambda *a, **k: None)

    foto = MagicMock()
    foto.content_type = "image/jpeg"

    async def _executar():
        threads["loop"] = threading.get_ident()
        return await mod.cadastrar_aluno_api(
            request=None,
            user_id=usuario_id,
            nome="João da Silva",
            email="aluno@teste.local",
            ra="RA1234",
            foto=foto,
            consentimento_biometrico=True,
            politica_versao="1.0",
            angulo="frontal",
            current_user={"sub": usuario_id, "role": "Aluno"},
        )

    resposta = asyncio.run(_executar())

    assert resposta["status"] == "sucesso"
    assert threads["persistir"] != threads["loop"], "S3/Rekognition rodaram no event loop"
