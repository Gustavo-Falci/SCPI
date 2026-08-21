"""Prova de fidelidade dos modelos de saída do lote 1 da etapa B do Swagger.

Cada teste daqui obtém o payload REAL da rota (handler de verdade, só o banco
e a AWS mockados) e o valida contra o modelo que a rota declara no /docs. Com
`extra="forbid"` nos modelos, a validação reprova nos dois sentidos: campo
documentado que a rota não devolve e campo devolvido que ninguém documentou.

Por isso o dado mockado é o dado REAL do lado de baixo — as colunas exatas do
SELECT, `uuid.UUID` onde a coluna é uuid, `datetime` onde é timestamp. Mock
enxuto passaria no teste e deixaria a documentação mentir em produção.
"""
import asyncio
import datetime
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from core.errors import rate_limit_handler
from core.limiter import limiter
from tests.conformidade_respostas import assert_resposta_conforme

ALUNO_ID = uuid.UUID("6f3a1c2e-8b44-4d19-9e77-2a5c0d1b4f83")
TURMA_ID = uuid.UUID("1b2c3d4e-5f60-4711-8899-aabbccddeeff")
HORARIO_ID = uuid.UUID("9a8b7c6d-5e4f-4031-9213-0f1e2d3c4b5a")


# --------------------------------------------------------------------------
# público
# --------------------------------------------------------------------------
def _client_publico():
    """App mínimo com o router público, no molde de test_health."""
    from routers import public

    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.include_router(public.router)
    return TestClient(app)


def test_raiz_conforme():
    assert_resposta_conforme(_client_publico().get("/"), "GET", "/")


def test_politica_privacidade_conforme():
    resposta = _client_publico().get("/politica-privacidade")
    assert_resposta_conforme(resposta, "GET", "/politica-privacidade")


def test_health_ok_conforme():
    cur = MagicMock()
    cur.fetchone.return_value = {"?column?": 1}
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    with patch("routers.public.get_db_cursor", return_value=cm):
        resposta = _client_publico().get("/health")
    assert resposta.status_code == 200
    assert_resposta_conforme(resposta, "GET", "/health")


def test_health_degradado_conforme():
    """O 503 também é documentado — e o corpo dele não passa pela rota, vem de
    um JSONResponse montado à mão, que é justamente onde um campo divergiria."""
    cm = MagicMock()
    cm.__enter__.return_value = None
    cm.__exit__.return_value = False
    with patch("routers.public.get_db_cursor", return_value=cm):
        resposta = _client_publico().get("/health")
    assert resposta.status_code == 503
    from schemas.respostas.public import SaudeDaApi

    SaudeDaApi.model_validate(resposta.json())


# --------------------------------------------------------------------------
# professores / turmas
# --------------------------------------------------------------------------
def _row_dashboard(**extra):
    return {
        "prof_nome": "Ana Prado",
        "chamada_id": 10,
        "turma_id": TURMA_ID,
        "total_aulas": 2,
        "nome_disciplina": "Cálculo I",
        "total": 5,
        "presentes": 3,
        "parciais": 1,
        "ausentes": 1,
        "aberta_chamada_id": None,
        "aberta_turma_id": None,
        "aberta_turma_nome": None,
    } | extra


def _aulas_hoje():
    return [
        {
            "id": HORARIO_ID,
            "turma_id": TURMA_ID,
            "nome": "Cálculo I",
            "horario": "19:00 - 20:40",
            "sala": "Lab 3",
        }
    ]


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {
            "aberta_chamada_id": 10,
            "aberta_turma_id": TURMA_ID,
            "aberta_turma_nome": "Cálculo I",
        },
    ],
    ids=["sem_chamada_ativa", "com_chamada_ativa"],
)
def test_dashboard_do_professor_conforme(extra):
    from routers.professores import get_dashboard

    with patch(
        "routers.professores.obter_dashboard_professor",
        return_value=_row_dashboard(**extra),
    ), patch(
        "routers.professores.listar_aulas_hoje_por_professor",
        return_value=_aulas_hoje(),
    ):
        resposta = get_dashboard(
            usuario_id="u1", current_user={"sub": "u1", "role": "Professor"}
        )
    assert_resposta_conforme(resposta, "GET", "/professor/dashboard/{usuario_id}")


def test_dashboard_sem_chamada_nenhuma_conforme():
    """Caminho do professor que nunca abriu chamada: estatísticas zeradas."""
    from routers.professores import get_dashboard

    with patch(
        "routers.professores.obter_dashboard_professor", return_value=None
    ), patch(
        "routers.professores.listar_aulas_hoje_por_professor", return_value=[]
    ):
        resposta = get_dashboard(
            usuario_id="u1", current_user={"sub": "u1", "role": "Professor"}
        )
    assert_resposta_conforme(resposta, "GET", "/professor/dashboard/{usuario_id}")


def test_turmas_do_professor_conforme():
    from routers.turmas import get_turmas

    rows = [
        {
            "turma_id": TURMA_ID,
            "nome_disciplina": "Cálculo I",
            "codigo_turma": "MAT-101",
            "dia_semana": None,
            "horario_inicio": None,
            "horario_fim": None,
            "chamada_aberta_id": 99,
        }
    ]
    with patch(
        "routers.turmas.listar_turmas_com_horarios_por_professor", return_value=rows
    ):
        resposta = get_turmas(
            usuario_id="u1", current_user={"sub": "u1", "role": "Professor"}
        )
    assert_resposta_conforme(resposta, "GET", "/turmas/{usuario_id}")


def test_turmas_com_horario_de_hoje_conforme():
    """`proximo_horario` montado a partir de `time` — o formato é texto pronto."""
    from routers.turmas import get_turmas

    rows = [
        {
            "turma_id": TURMA_ID,
            "nome_disciplina": "Cálculo I",
            "codigo_turma": "MAT-101",
            "dia_semana": datetime.datetime.now().weekday(),
            "horario_inicio": datetime.time(19, 0),
            "horario_fim": datetime.time(20, 40),
            "chamada_aberta_id": None,
        }
    ]
    with patch(
        "routers.turmas.listar_turmas_com_horarios_por_professor", return_value=rows
    ):
        resposta = get_turmas(
            usuario_id="u1", current_user={"sub": "u1", "role": "Professor"}
        )
    assert_resposta_conforme(resposta, "GET", "/turmas/{usuario_id}")


# --------------------------------------------------------------------------
# alunos (LGPD)
# --------------------------------------------------------------------------
def _preparar_consentimento(monkeypatch, ultimo, angulos=("frontal",)):
    monkeypatch.setattr(
        "routers.alunos.buscar_aluno_por_usuario_id", lambda _: {"aluno_id": ALUNO_ID}
    )
    monkeypatch.setattr("routers.alunos.obter_ultimo_evento", lambda _: ultimo)
    monkeypatch.setattr(
        "routers.alunos.listar_rostos_ativos_por_aluno",
        lambda _: [{"angulo": a} for a in angulos],
    )


@pytest.mark.parametrize(
    "ultimo",
    [
        None,
        {
            "evento": "aceite",
            "politica_versao": "1.0",
            "registrado_em": datetime.datetime(2026, 3, 12, 14, 22, 1),
        },
        {
            "evento": "revogacao",
            "politica_versao": "legado",
            "registrado_em": datetime.datetime(2026, 5, 1, 9, 0, 0),
        },
    ],
    ids=["nunca", "ativo", "revogado"],
)
def test_estado_do_consentimento_conforme(monkeypatch, ultimo):
    from routers.alunos import consentimento_estado

    _preparar_consentimento(monkeypatch, ultimo)
    resposta = consentimento_estado("u1", current_user={"sub": "u1", "role": "Aluno"})
    assert_resposta_conforme(resposta, "GET", "/aluno/consentimento/{usuario_id}")


def test_revogacao_de_biometria_conforme(monkeypatch):
    from routers.alunos import revogar_biometria

    monkeypatch.setattr(
        "routers.alunos.buscar_aluno_por_usuario_id", lambda _: {"aluno_id": ALUNO_ID}
    )
    monkeypatch.setattr(
        "routers.alunos.listar_rostos_ativos_por_aluno",
        lambda _: [
            {
                "face_id_rekognition": "f1",
                "s3_path_cadastro": "alunos/x.jpg",
                "angulo": "frontal",
            }
        ],
    )
    monkeypatch.setattr("routers.alunos.deletar_rosto", lambda _: None)
    monkeypatch.setattr("routers.alunos.s3_client", MagicMock())
    monkeypatch.setattr("routers.alunos.revogar_rosto_por_aluno", lambda _: 1)
    monkeypatch.setattr("routers.alunos.registrar_evento", lambda *a, **k: True)

    pedido = MagicMock()
    pedido.client = MagicMock(host="203.0.113.7")
    pedido.headers = {"user-agent": "Expo/1.0"}

    resposta = revogar_biometria(
        "u1", request=pedido, current_user={"sub": "u1", "role": "Aluno"}
    )
    assert_resposta_conforme(resposta, "DELETE", "/aluno/biometria/{usuario_id}")


# --------------------------------------------------------------------------
# chamadas (rotas de serviço, consumidas pela câmera)
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "row", [None, {"chamada_id": 42}], ids=["sem_chamada", "com_chamada"]
)
def test_chamada_aberta_por_sala_conforme(row):
    from routers.chamadas import chamada_aberta_por_sala

    with patch(
        "routers.chamadas.obter_chamada_aberta_por_sala", return_value=row
    ):
        resposta = chamada_aberta_por_sala(sala="Sala 101")
    assert_resposta_conforme(resposta, "GET", "/chamadas/aberta/sala")


@pytest.mark.parametrize(
    "motivo", [None, "ja_registrado"], ids=["presenca_nova", "idempotente"]
)
def test_presenca_da_camera_conforme(monkeypatch, motivo):
    from routers.chamadas import PresencaCameraPayload, registrar_presenca_camera
    import routers.chamadas as mod

    resultado = {
        "motivo": mod.MOTIVO_JA_REGISTRADO if motivo else None,
        "usuario_id": "u1",
        "aluno_nome": "Ana",
        "aluno_email": "ana@escola.local",
        "turma_nome": "Cálculo I",
    }
    monkeypatch.setattr(
        mod, "obter_chamada_aberta_por_sala", lambda _sala: {"chamada_id": 7}
    )
    monkeypatch.setattr(mod, "registrar_presenca_por_face", lambda _e, _c: resultado)

    resposta = asyncio.run(
        registrar_presenca_camera(
            payload=PresencaCameraPayload(
                external_image_id=str(ALUNO_ID), chamada_id=7
            ),
            background_tasks=BackgroundTasks(),
            sala="Sala 101",
        )
    )
    assert_resposta_conforme(
        resposta, "POST", "/chamadas/registrar_presenca_camera"
    )


# --------------------------------------------------------------------------
# relatórios (opções de filtro)
# --------------------------------------------------------------------------
def _opcoes_reais():
    """Saída REAL do repositório, montada com o cursor mockado.

    Fixar um dicionário à mão aqui provaria só que o dicionário à mão bate com
    o modelo. O que precisa bater é o que o repositório monta.
    """
    linhas = [
        {
            "turma_id": TURMA_ID,
            "nome_disciplina": "Cálculo I",
            "codigo_turma": "MAT-101",
            "turno": "Matutino",
            "semestre": "3",
            "professor_id": uuid.uuid4(),
            "professor_nome": "Ana",
        },
        {
            "turma_id": uuid.uuid4(),
            "nome_disciplina": "Física",
            "codigo_turma": "FIS-201",
            "turno": "Noturno",
            "semestre": "5",
            "professor_id": uuid.uuid4(),
            "professor_nome": "Bruno",
        },
    ]
    cur = MagicMock()
    cur.fetchall.return_value = linhas
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_opcoes_filtros_relatorios

        return listar_opcoes_filtros_relatorios()


def test_opcoes_de_filtro_do_professor_conforme():
    from routers.relatorios import opcoes_filtros_relatorios_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), patch(
        "routers.relatorios.opcoes_filtros_relatorios", return_value=_opcoes_reais()
    ):
        resposta = opcoes_filtros_relatorios_professor(
            current_user={"sub": "u1", "role": "Professor"}
        )
    assert_resposta_conforme(resposta, "GET", "/professor/relatorios/filtros")


def test_opcoes_de_filtro_do_admin_conforme():
    from routers.relatorios import opcoes_filtros_relatorios_admin

    with patch(
        "routers.relatorios.opcoes_filtros_relatorios", return_value=_opcoes_reais()
    ):
        resposta = opcoes_filtros_relatorios_admin(
            current_user={"sub": "adm", "role": "Admin"}
        )
    assert_resposta_conforme(resposta, "GET", "/admin/relatorios/filtros")


def test_opcoes_de_filtro_vazias_conforme():
    """Banco fora do ar devolve a estrutura vazia — que também é documentada."""
    from routers.relatorios import opcoes_filtros_relatorios_admin

    vazio = {"turmas": [], "professores": [], "turnos": [], "semestres": []}
    with patch("routers.relatorios.opcoes_filtros_relatorios", return_value=vazio):
        resposta = opcoes_filtros_relatorios_admin(
            current_user={"sub": "adm", "role": "Admin"}
        )
    assert_resposta_conforme(resposta, "GET", "/admin/relatorios/filtros")


# --------------------------------------------------------------------------
# admin
# --------------------------------------------------------------------------
@pytest.fixture
def client_admin():
    """TestClient autenticado como Admin (o router /admin exige require_role)."""
    from api import app
    from core.security import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "admin@teste.local",
        "role": "Admin",
    }
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_lista_de_alunos_do_admin_conforme(client_admin):
    """As chaves do item são as colunas do SELECT de `listar_alunos_para_admin`
    (menos `total_geral`, que o repositório retira antes de devolver)."""
    item = {
        "aluno_id": ALUNO_ID,
        "ra": "20260001",
        "nome": "Ana Prado",
        "email": "ana@escola.local",
        "turno": "Noturno",
        "turmas_count": 2,
        "tem_biometria": True,
        "ja_matriculado": False,
    }
    with patch(
        "routers.admin.listar_alunos_para_admin",
        return_value={"items": [item], "total": 1},
    ), patch("routers.admin.contar_alunos_pendentes", return_value=3):
        resposta = client_admin.get("/admin/alunos")
    assert resposta.status_code == 200
    assert_resposta_conforme(resposta, "GET", "/admin/alunos")


def _registros_inventario():
    return [
        {
            "face_id_rekognition": "face-ativa",
            "s3_path_cadastro": "alunos/ana-frontal.jpg",
            "angulo": "frontal",
            "revogado_em": None,
            "aluno_id": ALUNO_ID,
            "nome": "Ana Prado",
            "ra": "20260001",
        },
        {
            "face_id_rekognition": "face-revogada",
            "s3_path_cadastro": "alunos/ana-esquerda.jpg",
            "angulo": "esquerda",
            "revogado_em": datetime.datetime(2026, 6, 1, 10, 0, 0),
            "aluno_id": ALUNO_ID,
            "nome": "Ana Prado",
            "ra": "20260001",
        },
    ]


def test_inventario_biometrico_conforme(client_admin):
    """Cobre os três status de uma vez: ok, revogado e órfão."""
    faces = (
        [
            {
                "face_id": "face-ativa",
                "external_image_id": str(ALUNO_ID),
                "image_id": "img-1",
            },
            {
                "face_id": "face-revogada",
                "external_image_id": str(ALUNO_ID),
                "image_id": "img-2",
            },
            {"face_id": "face-orfa", "external_image_id": None, "image_id": "img-3"},
        ],
        True,
    )
    objetos = (
        [
            {
                "key": "alunos/ana-frontal.jpg",
                "size": 51234,
                "last_modified": "2026-06-01T10:00:00+00:00",
            },
            {"key": "alunos/orfao.jpg", "size": 12, "last_modified": None},
        ],
        True,
    )
    with patch("routers.admin.listar_todas_faces", return_value=faces), patch(
        "routers.admin.listar_todos_objetos_s3", return_value=objetos
    ), patch(
        "routers.admin.listar_inventario_biometrico",
        return_value=_registros_inventario(),
    ):
        resposta = client_admin.get("/admin/rostos/inventario")
    assert resposta.status_code == 200
    assert_resposta_conforme(resposta, "GET", "/admin/rostos/inventario")


def test_inventario_com_aws_indisponivel_conforme(client_admin):
    """Degradação por lado: `indisponivel` preenchido é resposta prevista."""
    with patch(
        "routers.admin.listar_todas_faces", return_value=([], False)
    ), patch(
        "routers.admin.listar_todos_objetos_s3", return_value=([], False)
    ), patch(
        "routers.admin.listar_inventario_biometrico",
        return_value=_registros_inventario(),
    ):
        resposta = client_admin.get("/admin/rostos/inventario")
    assert sorted(resposta.json()["indisponivel"]) == ["rekognition", "s3"]
    assert_resposta_conforme(resposta, "GET", "/admin/rostos/inventario")
