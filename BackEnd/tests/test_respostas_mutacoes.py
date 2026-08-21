"""Prova de fidelidade dos modelos de saída do lote 3: a família de mutações.

Vinte e uma rotas que criam, alteram ou apagam. Quinze devolvem só
`{"mensagem": ...}`; as outras seis acrescentam o id que o backend gerou ou a
contagem do lote enviado — e é justamente esse punhado de campos extras que a
documentação precisa distinguir, porque olhando de fora todas parecem iguais.

Ao contrário dos lotes 1 e 2, aqui quase nenhuma rota tinha teste exercitando o
handler: a regra "nada declarado sem prova" obrigou a escrever o teste antes do
modelo. Os handlers são chamados direto, com as dependências de rota fora do
caminho e o repositório/AWS mockados — o que se afirma é o FORMATO da resposta
de sucesso, não a regra de negócio, que tem testes próprios.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import BackgroundTasks

from tests.conformidade_respostas import assert_resposta_conforme

ADMIN = {"sub": "admin@teste.local", "role": "Admin"}
PROFESSOR = {"sub": "prof@teste.local", "role": "Professor"}
TURMA_ID = "1b2c3d4e-5f60-4711-8899-aabbccddeeff"
ALUNO_ID = "6f3a1c2e-8b44-4d19-9e77-2a5c0d1b4f83"


@pytest.fixture
def pedido():
    """Request suficiente para `client_ip` e para o log de auditoria."""
    req = MagicMock()
    req.client = MagicMock(host="203.0.113.7")
    req.headers = {"user-agent": "portal/1.0"}
    return req


# --------------------------------------------------------------------------
# admin — turmas, horários e matrículas
# --------------------------------------------------------------------------
def test_criar_turma_conforme(pedido):
    from routers.admin import admin_criar_turma
    from schemas.admin import TurmaCreate

    turma = TurmaCreate(
        professor_id=None,
        codigo_turma="MAT-101",
        nome_disciplina="Cálculo I",
        periodo_letivo="2026/2",
        sala_padrao="Lab 3",
        turno="Noturno",
        semestre="3",
    )
    with patch("routers.admin.criar_turma"):
        resposta = admin_criar_turma(turma, request=pedido, current_user=ADMIN)
    # O id é gerado no backend: sem ele na resposta o portal não referencia a
    # turma que acabou de criar.
    assert uuid.UUID(resposta["turma_id"])
    assert_resposta_conforme(resposta, "POST", "/admin/turmas")


@pytest.mark.parametrize("professor_id", [None, "p1"], ids=["remove", "atribui"])
def test_atribuir_professor_conforme(pedido, professor_id):
    from routers.admin import admin_atribuir_professor
    from schemas.admin import AtribuirProfessor

    with patch("routers.admin.atribuir_professor_turma", return_value=1):
        resposta = admin_atribuir_professor(
            TURMA_ID,
            AtribuirProfessor(professor_id=professor_id),
            request=pedido,
            current_user=ADMIN,
        )
    assert_resposta_conforme(resposta, "PATCH", "/admin/turmas/{turma_id}/professor")


def test_adicionar_horario_conforme(pedido):
    from routers.admin import admin_adicionar_horario
    from schemas.admin import HorarioCreate

    horario = HorarioCreate(
        turma_id=TURMA_ID,
        dia_semana=2,
        horario_inicio="19:00",
        horario_fim="20:40",
        sala="Lab 3",
    )
    with patch("routers.admin.detectar_conflito_horario", return_value=None), patch(
        "routers.admin.inserir_horario"
    ):
        resposta = admin_adicionar_horario(horario, request=pedido, current_user=ADMIN)
    assert_resposta_conforme(resposta, "POST", "/admin/horarios")


def test_excluir_turma_conforme(pedido):
    from routers.admin import admin_excluir_turma

    with patch("routers.admin.excluir_turma_em_cascata"):
        resposta = admin_excluir_turma(TURMA_ID, request=pedido, current_user=ADMIN)
    assert_resposta_conforme(resposta, "DELETE", "/admin/turmas/{turma_id}")


def test_excluir_horario_conforme(pedido):
    from routers.admin import admin_excluir_horario

    with patch("routers.admin.excluir_horario"):
        resposta = admin_excluir_horario(
            "9a8b7c6d-5e4f-4031-9213-0f1e2d3c4b5a", request=pedido, current_user=ADMIN
        )
    assert_resposta_conforme(resposta, "DELETE", "/admin/horarios/{horario_id}")


def test_matricular_alunos_conforme(pedido):
    """`total_enviados` é o tamanho do pedido; o quanto mudou vai na mensagem."""
    from routers.admin import admin_matricular_alunos
    from schemas.admin import MatricularAlunos

    with patch(
        "routers.admin.obter_turno_turma", return_value={"turno": "Noturno"}
    ), patch("routers.admin.listar_alunos_por_ids", return_value=[]), patch(
        "routers.admin.matricular_alunos_em_turma", return_value=1
    ):
        resposta = admin_matricular_alunos(
            TURMA_ID,
            MatricularAlunos(aluno_ids=[ALUNO_ID, str(uuid.uuid4())]),
            request=pedido,
            current_user=ADMIN,
        )
    # Dois enviados, um matriculado: duplicata é ignorada em silêncio.
    assert resposta["total_enviados"] == 2
    assert_resposta_conforme(
        resposta, "POST", "/admin/turmas/{turma_id}/matricular-alunos"
    )


def test_desmatricular_alunos_conforme(pedido):
    from routers.admin import admin_desmatricular_alunos
    from schemas.admin import MatricularAlunos

    with patch(
        "routers.admin.obter_turno_turma", return_value={"turno": "Noturno"}
    ), patch("routers.admin.desmatricular_alunos_da_turma", return_value=1):
        resposta = admin_desmatricular_alunos(
            TURMA_ID,
            MatricularAlunos(aluno_ids=[ALUNO_ID]),
            request=pedido,
            current_user=ADMIN,
        )
    assert_resposta_conforme(
        resposta, "POST", "/admin/turmas/{turma_id}/desmatricular-alunos"
    )


# --------------------------------------------------------------------------
# admin — pessoas
# --------------------------------------------------------------------------
def test_atualizar_aluno_conforme(pedido):
    from routers.admin import admin_atualizar_aluno
    from schemas.admin import AtualizarAlunoAdmin

    with patch("routers.admin.atualizar_aluno", return_value=True):
        resposta = admin_atualizar_aluno(
            ALUNO_ID,
            AtualizarAlunoAdmin(nome="Ana Prado"),
            request=pedido,
            current_user=ADMIN,
        )
    assert_resposta_conforme(resposta, "PATCH", "/admin/alunos/{aluno_id}")


def test_excluir_aluno_conforme(pedido):
    from routers.admin import admin_excluir_aluno

    with patch("routers.admin.listar_rostos_ativos_por_aluno", return_value=[]), patch(
        "routers.admin.excluir_aluno_em_cascata", return_value="u1"
    ):
        resposta = admin_excluir_aluno(ALUNO_ID, request=pedido, current_user=ADMIN)
    assert_resposta_conforme(resposta, "DELETE", "/admin/alunos/{aluno_id}")


def test_atualizar_professor_conforme(pedido):
    from routers.admin import admin_atualizar_professor
    from schemas.admin import AtualizarProfessorAdmin

    with patch("routers.admin.atualizar_professor", return_value=True):
        resposta = admin_atualizar_professor(
            "p1",
            AtualizarProfessorAdmin(nome="Ana Prado"),
            request=pedido,
            current_user=ADMIN,
        )
    assert_resposta_conforme(resposta, "PATCH", "/admin/professores/{professor_id}")


def test_excluir_professor_conforme(pedido):
    from routers.admin import admin_excluir_professor

    with patch("routers.admin.excluir_professor_em_cascata", return_value="u1"):
        resposta = admin_excluir_professor("p1", request=pedido, current_user=ADMIN)
    assert_resposta_conforme(resposta, "DELETE", "/admin/professores/{professor_id}")


def test_criar_professor_conforme(pedido):
    """A senha temporária NÃO entra na resposta — vai por e-mail."""
    from routers.admin import admin_criar_professor
    from schemas.admin import CriarProfessorAdmin

    with patch("routers.admin.buscar_usuario_por_email", return_value=None), patch(
        # pbkdf2 real são 600k iterações; aqui só o formato da resposta importa.
        "routers.admin.get_password_hash",
        return_value="hash-fake",
    ), patch("routers.admin.criar_professor_com_usuario"):
        resposta = admin_criar_professor(
            CriarProfessorAdmin(nome="Ana Prado", email="ana@escola.com.br"),
            request=pedido,
            background_tasks=BackgroundTasks(),
            current_user=ADMIN,
        )
    assert "senha" not in resposta and "senha_temporaria" not in resposta
    assert_resposta_conforme(resposta, "POST", "/admin/usuarios/professor")


def test_criar_aluno_conforme(pedido):
    """Dois ids: `usuario_id` é o login, `aluno_id` é o cadastro acadêmico."""
    from routers.admin import admin_criar_aluno
    from schemas.admin import CriarAlunoAdmin

    # `existe_aluno_por_ra` precisa entrar aqui: sem ele o handler faz consulta
    # de verdade, e o `.env` da raiz aponta para o banco de PRODUÇÃO. O teste
    # ainda passava (a falha de conexão devolve falsy), só que gastando dois
    # connect-timeouts — 20s presos numa suíte que roda inteira em 10s.
    with patch("routers.admin.buscar_usuario_por_email", return_value=None), patch(
        "routers.admin.existe_aluno_por_ra", return_value=False
    ), patch("routers.admin.get_password_hash", return_value="hash-fake"), patch(
        "routers.admin.criar_aluno_com_usuario"
    ):
        resposta = admin_criar_aluno(
            CriarAlunoAdmin(
                nome="Ana Prado", email="ana@escola.com.br", ra="20260001", turno="Noturno"
            ),
            request=pedido,
            background_tasks=BackgroundTasks(),
            current_user=ADMIN,
        )
    assert resposta["usuario_id"] != resposta["aluno_id"]
    assert_resposta_conforme(resposta, "POST", "/admin/usuarios/aluno")


# --------------------------------------------------------------------------
# admin — limpeza da biometria (AWS direto, sem banco)
# --------------------------------------------------------------------------
def test_excluir_rostos_rekognition_bulk_conforme(pedido):
    from routers.admin import admin_excluir_rostos_rekognition_bulk, BulkFaceIds

    with patch("routers.admin.rekognition_client", MagicMock()):
        resposta = admin_excluir_rostos_rekognition_bulk(
            BulkFaceIds(face_ids=["f1", "f2"]), request=pedido, current_user=ADMIN
        )
    assert_resposta_conforme(resposta, "DELETE", "/admin/rostos/rekognition/bulk")


def test_excluir_rosto_rekognition_conforme(pedido):
    from routers.admin import admin_excluir_rosto_rekognition

    with patch("routers.admin.rekognition_client", MagicMock()):
        resposta = admin_excluir_rosto_rekognition(
            "f1", request=pedido, current_user=ADMIN
        )
    assert_resposta_conforme(resposta, "DELETE", "/admin/rostos/rekognition/{face_id}")


def test_excluir_rosto_s3_conforme(pedido):
    from routers.admin import admin_excluir_rosto_s3, S3KeyPayload

    with patch("routers.admin.s3_client", MagicMock()):
        resposta = admin_excluir_rosto_s3(
            S3KeyPayload(key="alunos/ana-frontal.jpg"), request=pedido, current_user=ADMIN
        )
    assert_resposta_conforme(resposta, "DELETE", "/admin/rostos/s3")


# --------------------------------------------------------------------------
# chamadas
# --------------------------------------------------------------------------
def test_abrir_chamada_conforme():
    from routers.chamadas import abrir_chamada
    from schemas.chamada import ChamadaAbrir

    with patch("routers.chamadas.obter_professor_id", return_value="p1"), patch(
        "routers.chamadas.professor_responsavel_pela_turma", return_value=True
    ), patch(
        "routers.chamadas.existe_aula_no_horario_atual_para_turma", return_value=True
    ), patch("routers.chamadas.abrir_chamada_para_turma", return_value=7):
        resposta = abrir_chamada(
            ChamadaAbrir(turma_id=TURMA_ID), current_user=PROFESSOR
        )
    assert resposta["chamada_id"] == 7
    assert_resposta_conforme(resposta, "POST", "/chamadas/abrir")


def test_fechar_chamada_conforme():
    from routers.chamadas import fechar_chamada

    with patch("routers.chamadas.obter_professor_id", return_value="p1"), patch(
        "routers.chamadas.professor_responsavel_pela_turma", return_value=True
    ), patch(
        "routers.chamadas.obter_chamada_aberta_com_disciplina",
        return_value={"chamada_id": 7, "nome_disciplina": "Cálculo I"},
    ), patch("routers.chamadas.fechar_chamadas_abertas_por_turma"):
        resposta = fechar_chamada(
            TURMA_ID, background_tasks=BackgroundTasks(), current_user=PROFESSOR
        )
    assert_resposta_conforme(resposta, "POST", "/chamadas/fechar/{turma_id}")


def _payload_presencas():
    from schemas.chamada import FinalizarChamadaPayload, PresencaAluno

    return FinalizarChamadaPayload(
        alunos=[PresencaAluno(aluno_id=ALUNO_ID, aulas_presentes=[1, 2])]
    )


def test_ajustar_chamada_conforme():
    from routers.chamadas import ajustar_chamada

    with patch("routers.chamadas.obter_professor_id", return_value="p1"), patch(
        "routers.chamadas.professor_responsavel_pela_turma", return_value=True
    ), patch(
        "routers.chamadas.obter_chamada_por_id",
        return_value={"chamada_id": 7, "turma_id": TURMA_ID, "nome_disciplina": "Cálculo I"},
    ), patch("routers.chamadas.ajustar_presencas_chamada"):
        resposta = ajustar_chamada(7, _payload_presencas(), current_user=PROFESSOR)
    assert_resposta_conforme(resposta, "POST", "/chamadas/{chamada_id}/ajustar")


def test_finalizar_chamada_conforme():
    from routers.chamadas import finalizar_chamada

    with patch("routers.chamadas.obter_professor_id", return_value="p1"), patch(
        "routers.chamadas.professor_responsavel_pela_turma", return_value=True
    ), patch(
        "routers.chamadas.obter_chamada_por_id",
        return_value={"chamada_id": 7, "turma_id": TURMA_ID, "nome_disciplina": "Cálculo I"},
    ), patch("routers.chamadas.ajustar_presencas_chamada"), patch(
        "routers.chamadas.fechar_chamadas_abertas_por_turma"
    ):
        resposta = finalizar_chamada(
            7,
            _payload_presencas(),
            background_tasks=BackgroundTasks(),
            current_user=PROFESSOR,
        )
    assert_resposta_conforme(resposta, "POST", "/chamadas/{chamada_id}/finalizar")


# --------------------------------------------------------------------------
# notificações
# --------------------------------------------------------------------------
def test_registrar_push_token_conforme():
    from routers.notificacoes import registrar_push_token
    from schemas.auth import RegisterTokenBody

    with patch("routers.notificacoes.upsert_push_token"):
        resposta = registrar_push_token(
            RegisterTokenBody(expo_token="ExponentPushToken[abc123def456]"),
            current_user={"sub": "u1", "role": "Aluno"},
        )
    assert_resposta_conforme(resposta, "POST", "/notificacoes/registrar-token")
