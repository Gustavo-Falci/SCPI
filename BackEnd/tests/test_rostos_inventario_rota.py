"""Testes da rota GET /admin/rostos/inventario — AWS e banco mockados."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """TestClient autenticado como Admin (o router /admin exige require_role)."""
    from api import app
    from core.security import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"sub": "admin@teste.local", "role": "Admin"}
    yield TestClient(app)
    app.dependency_overrides.clear()


def _patches(faces=([], True), objetos=([], True), registros=None):
    return (
        patch("routers.admin.listar_todas_faces", return_value=faces),
        patch("routers.admin.listar_todos_objetos_s3", return_value=objetos),
        patch("routers.admin.listar_inventario_biometrico", return_value=registros or []),
    )


def test_envelope_tem_as_cinco_chaves(client):
    p1, p2, p3 = _patches()
    with p1, p2, p3:
        r = client.get("/admin/rostos/inventario")
    assert r.status_code == 200
    assert set(r.json()) == {"rekognition", "s3", "alunos", "resumo", "indisponivel"}


def test_face_orfa_chega_classificada(client):
    faces = ([{"face_id": "f1", "external_image_id": "ana", "image_id": "i1"}], True)
    p1, p2, p3 = _patches(faces=faces)
    with p1, p2, p3:
        r = client.get("/admin/rostos/inventario")
    item = r.json()["rekognition"][0]
    assert item["status"] == "orfao"
    assert r.json()["resumo"]["rekognition"]["orfaos"] == 1


def test_falha_no_s3_marca_lado_indisponivel(client):
    p1, p2, p3 = _patches(objetos=([], False))
    with p1, p2, p3:
        r = client.get("/admin/rostos/inventario")
    assert r.json()["indisponivel"] == ["s3"]


def test_falha_no_rekognition_marca_lado_indisponivel(client):
    p1, p2, p3 = _patches(faces=([], False))
    with p1, p2, p3:
        r = client.get("/admin/rostos/inventario")
    assert r.json()["indisponivel"] == ["rekognition"]


def test_os_dois_lados_fora_do_ar(client):
    p1, p2, p3 = _patches(faces=([], False), objetos=([], False))
    with p1, p2, p3:
        r = client.get("/admin/rostos/inventario")
    assert sorted(r.json()["indisponivel"]) == ["rekognition", "s3"]


def test_lado_indisponivel_nao_derruba_o_outro(client):
    """Com endpoint único, uma falha da AWS não pode zerar a tela inteira."""
    faces = ([{"face_id": "f1", "external_image_id": "ana", "image_id": "i1"}], True)
    p1, p2, p3 = _patches(faces=faces, objetos=([], False))
    with p1, p2, p3:
        r = client.get("/admin/rostos/inventario")
    assert len(r.json()["rekognition"]) == 1


def test_rotas_antigas_sumiram(client):
    """405 em /rostos/s3 é esperado: o DELETE continua lá, só o GET saiu."""
    assert client.get("/admin/rostos/rekognition").status_code == 404
    assert client.get("/admin/rostos/s3").status_code in (404, 405)


def test_exige_admin():
    """Sem override de autenticação, a rota não responde 200.

    Sem `with`: o context manager do TestClient dispara os eventos de startup,
    que rodam as migrations e tentam conectar no banco do .env — produção.
    """
    from api import app

    sem_auth = TestClient(app)
    assert sem_auth.get("/admin/rostos/inventario").status_code in (401, 403)
