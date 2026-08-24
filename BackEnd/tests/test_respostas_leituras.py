"""Prova de fidelidade dos modelos de saída do lote 4: as leituras que sobraram.

Treze rotas de consulta — listagens do portal Admin, as telas do aluno, a
turma vista pelo professor, o estado da chamada e a confirmação de sessão.
Diferente das mutações do lote 3, aqui a forma da resposta é a forma do
SELECT: o handler devolve as linhas quase como vieram do banco, então o que
este arquivo trava é o CONTRATO da consulta, não a regra de negócio.

Como nas rotas do lote 3, nenhuma delas tinha teste exercitando o handler. Os
handlers são chamados direto, com as dependências de rota fora do caminho e
TODO repositório mockado — repositório esquecido no `patch` faz consulta de
verdade contra o banco que o `.env` da raiz aponta (produção), devolve falsy
por timeout e o teste passa assim mesmo, só mais lento.

As linhas falsas usam os tipos que o psycopg2 realmente devolve
(`uuid.UUID` em coluna `uuid`, `datetime.time` em coluna `time`), não a
string já serializada: é o `jsonable_encoder` dentro do apoio de conformidade
que faz a conversão, e é ela que o cliente enxerga.
"""
import datetime
import uuid
from unittest.mock import patch

import pytest
from starlette.requests import Request

from tests.conformidade_respostas import assert_resposta_conforme

ADMIN = {"sub": "admin@teste.local", "role": "Admin"}
ALUNO_USUARIO_ID = "3f9c1d7a-2b55-4e10-9a88-77c0d1b4e520"
PROF_USUARIO_ID = "8c2e4a91-6d13-4f77-bb02-1e5a9c3d7f44"
ALUNO = {"sub": ALUNO_USUARIO_ID, "role": "Aluno"}
PROFESSOR = {"sub": PROF_USUARIO_ID, "role": "Professor"}
TURMA_ID = uuid.UUID("1b2c3d4e-5f60-4711-8899-aabbccddeeff")
ALUNO_ID = uuid.UUID("6f3a1c2e-8b44-4d19-9e77-2a5c0d1b4f83")
PROFESSOR_ID = uuid.UUID("b70c5d21-9e34-4a68-8f15-3c6d2e0a9b71")
HORARIO_ID = uuid.UUID("d41f6a08-7c92-4b35-90ae-5f2c8d1b6033")


# --------------------------------------------------------------------------
# admin — as listagens que alimentam o portal
# --------------------------------------------------------------------------
def test_listar_professores_conforme():
    from routers.admin import admin_listar_professores

    linhas = [{"professor_id": PROFESSOR_ID, "nome": "Ana Prado", "email": "ana@escola.local"}]
    with patch("routers.admin.listar_professores_para_admin", return_value=linhas):
        resposta = admin_listar_professores()

    assert_resposta_conforme(resposta, "GET", "/admin/professores")


def test_listar_professores_vazio_conforme():
    """Lista vazia é resposta normal — e é o que sai quando o banco está fora."""
    from routers.admin import admin_listar_professores

    with patch("routers.admin.listar_professores_para_admin", return_value=[]):
        resposta = admin_listar_professores()

    assert resposta == []
    assert_resposta_conforme(resposta, "GET", "/admin/professores")


@pytest.mark.parametrize(
    "professor_nome,periodo,turno,semestre",
    [
        ("Ana Prado", "2026/2", "Noturno", "3"),
        # Turma sem professor não vem com `null`: o SELECT já troca por texto.
        # Os outros três são colunas anuláveis de Turmas.
        ("Sem professor", None, None, None),
    ],
    ids=["com-professor", "sem-professor-e-sem-periodo"],
)
def test_listar_turmas_completas_conforme(professor_nome, periodo, turno, semestre):
    from routers.admin import admin_listar_turmas

    linhas = [
        {
            "turma_id": TURMA_ID,
            "nome_disciplina": "Cálculo I",
            "codigo_turma": "MAT-101",
            "turno": turno,
            "semestre": semestre,
            "periodo_letivo": periodo,
            "professor_nome": professor_nome,
            "total_alunos": 27,
        }
    ]
    with patch("routers.admin.listar_turmas_completas", return_value=linhas):
        resposta = admin_listar_turmas()

    assert_resposta_conforme(resposta, "GET", "/admin/turmas-completas")


def test_listar_horarios_completos_conforme():
    from routers.admin import admin_listar_todos_horarios

    linhas = [
        {
            # `inicio`/`fim` já saem do SELECT como texto "HH:MM" (to_char),
            # não como `time` — quem lê monta a grade sem reformatar.
            "horario_id": HORARIO_ID,
            "turma_id": TURMA_ID,
            "dia_semana": 2,
            "inicio": "19:00",
            "fim": "20:40",
            "sala": "Lab 3",
            "nome_disciplina": "Cálculo I",
            "turno": "Noturno",
            "semestre": "3",
        }
    ]
    with patch("routers.admin.listar_horarios_completos", return_value=linhas):
        resposta = admin_listar_todos_horarios()

    assert_resposta_conforme(resposta, "GET", "/admin/horarios-todos")


def test_listar_alunos_da_turma_admin_conforme():
    """O handler renomeia `id` para `aluno_id` — a rota do professor não faz isso."""
    from routers.admin import admin_listar_alunos_turma

    linhas = [{"id": ALUNO_ID, "nome": "Bruno Lima", "email": "bruno@escola.local", "ra": "2026001"}]
    with patch("routers.admin.listar_alunos_da_turma", return_value=linhas):
        resposta = admin_listar_alunos_turma(str(TURMA_ID))

    assert resposta[0]["aluno_id"] == ALUNO_ID
    assert_resposta_conforme(resposta, "GET", "/admin/turmas/{turma_id}/alunos")


# --------------------------------------------------------------------------
# aluno — as telas do app
# --------------------------------------------------------------------------
def test_dashboard_aluno_conforme():
    from routers.alunos import get_dashboard_aluno

    linha = {
        "user_nome": "Bruno Lima",
        "aluno_id": ALUNO_ID,
        "turno": "Noturno",
        "total_presencas": 18,
        "total_chamadas": 20,
    }
    aulas = [{"id": HORARIO_ID, "nome": "Cálculo I", "horario": "19:00 - 20:40", "sala": "Lab 3"}]
    with patch("routers.alunos.obter_dashboard_aluno", return_value=linha), \
         patch("routers.alunos.listar_aulas_hoje_por_aluno", return_value=aulas):
        resposta = get_dashboard_aluno(ALUNO_USUARIO_ID, current_user=ALUNO)

    assert resposta["frequencia_geral"] == 90
    assert_resposta_conforme(resposta, "GET", "/aluno/dashboard/{usuario_id}")


def test_dashboard_aluno_sem_chamadas_conforme():
    """Sem chamada fechada, `frequencia_geral` é 0 (não `null`) e não há divisão."""
    from routers.alunos import get_dashboard_aluno

    linha = {
        "user_nome": "Bruno Lima",
        "aluno_id": ALUNO_ID,
        "turno": None,
        "total_presencas": 0,
        "total_chamadas": 0,
    }
    with patch("routers.alunos.obter_dashboard_aluno", return_value=linha), \
         patch("routers.alunos.listar_aulas_hoje_por_aluno", return_value=[]):
        resposta = get_dashboard_aluno(ALUNO_USUARIO_ID, current_user=ALUNO)

    assert resposta["frequencia_geral"] == 0
    assert_resposta_conforme(resposta, "GET", "/aluno/dashboard/{usuario_id}")


def test_frequencias_do_aluno_conforme():
    from routers.alunos import get_frequencias_detalhadas

    linhas = [
        {
            "turma_id": TURMA_ID,
            "nome": "Cálculo I",
            "codigo_turma": "MAT-101",
            "total_aulas": 20,
            "presencas": 15,
        },
        # Turma que ainda não teve aula fechada: percentual 0, sem divisão por zero.
        {
            "turma_id": uuid.UUID("2c3d4e5f-6071-4822-99aa-bbccddeeff00"),
            "nome": "Álgebra Linear",
            "codigo_turma": "MAT-102",
            "total_aulas": 0,
            "presencas": 0,
        },
    ]
    with patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": ALUNO_ID}), \
         patch("routers.alunos.listar_frequencias_por_aluno", return_value=linhas):
        resposta = get_frequencias_detalhadas(ALUNO_USUARIO_ID, current_user=ALUNO)

    assert resposta["media_geral"] == 75
    assert resposta["frequencias"][1]["presenca"] == 0
    assert_resposta_conforme(resposta, "GET", "/aluno/frequencias/{usuario_id}")


def test_historico_de_chamadas_conforme():
    """`dia_semana` é calculado no handler a partir de `dia_iso`, e os dois vão
    na resposta — o app mostra a sigla e ordena pelo número."""
    from routers.alunos import get_historico_chamadas_aluno

    linhas = [
        {
            "chamada_id": 41,
            "data_chamada": "12/08/2026",
            "dia_iso": 3,
            "horario_inicio": "19:00",
            "horario_fim": "20:40",
            "total_aulas": 2,
            "aulas_presentes_count": 1,
            "presente": True,
            "tipo_registro": "Biometria",
        }
    ]
    with patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": ALUNO_ID}), \
         patch("routers.alunos.aluno_pertence_turma", return_value=True), \
         patch("routers.alunos.obter_turma_basica",
               return_value={"nome_disciplina": "Cálculo I", "codigo_turma": "MAT-101"}), \
         patch("routers.alunos.listar_historico_chamadas_aluno", return_value=linhas):
        resposta = get_historico_chamadas_aluno(
            ALUNO_USUARIO_ID, str(TURMA_ID), current_user=ALUNO
        )

    # Presente em 1 das 2 aulas do slot: conta como parcial, não como presença cheia.
    assert resposta["parciais"] == 1
    assert resposta["chamadas"][0]["dia_semana"] == "Qua"
    assert_resposta_conforme(resposta, "GET", "/aluno/historico-chamadas/{usuario_id}")


def test_foto_de_biometria_conforme():
    """`expira_em_segundos` é constante (300) e acompanha a URL presigned: sem
    ele o app não sabe quando parar de reusar o link."""
    from routers.alunos import obter_foto_biometria

    with patch("routers.alunos.obter_path_biometria_por_usuario",
               return_value={"s3_path_cadastro": "biometria/aluno.jpg"}), \
         patch("routers.alunos.gerar_url_presigned", return_value="https://s3.local/assinada"):
        resposta = obter_foto_biometria(ALUNO_USUARIO_ID, current_user=ALUNO)

    assert resposta["expira_em_segundos"] == 300
    assert_resposta_conforme(resposta, "GET", "/aluno/biometria-foto/{usuario_id}")


@pytest.mark.parametrize(
    "angulos,completo",
    [
        (["frontal", "esquerda", "direita", "cima"], True),
        (["frontal"], False),
    ],
    ids=["completo", "incompleto"],
)
def test_status_dos_angulos_conforme(angulos, completo):
    from routers.alunos import status_angulos_face

    rostos = [{"face_id_rekognition": f"f{i}", "s3_path_cadastro": f"p{i}", "angulo": a}
              for i, a in enumerate(angulos)]
    with patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": ALUNO_ID}), \
         patch("routers.alunos.listar_rostos_ativos_por_aluno", return_value=rostos):
        resposta = status_angulos_face(ALUNO_USUARIO_ID, current_user=ALUNO)

    assert resposta["completo"] is completo
    assert_resposta_conforme(resposta, "GET", "/alunos/status-angulos-face/{usuario_id}")


# --------------------------------------------------------------------------
# turma e chamada — as telas do professor
# --------------------------------------------------------------------------
def test_alunos_da_turma_conforme():
    """Aqui a chave é `id`, não `aluno_id`: a rota devolve a linha do SELECT sem
    renomear, ao contrário da rota equivalente do Admin."""
    from routers.turmas import get_alunos_turma

    linhas = [{"id": ALUNO_ID, "nome": "Bruno Lima", "email": "bruno@escola.local", "ra": "2026001"}]
    with patch("routers.turmas.professor_responsavel_por_usuario", return_value=True), \
         patch("routers.turmas.listar_alunos_da_turma", return_value=linhas):
        resposta = get_alunos_turma(str(TURMA_ID), current_user=PROFESSOR)

    assert_resposta_conforme(resposta, "GET", "/turmas/{turma_id}/alunos")


def test_status_da_chamada_aberta_conforme():
    from routers.chamadas import status_chamada

    chamada = {"chamada_id": 41, "horario_inicio": datetime.time(19, 0)}
    with patch("routers.chamadas.obter_chamada_aberta_por_turma", return_value=chamada), \
         patch("routers.chamadas.contar_alunos_da_turma", return_value=27), \
         patch("routers.chamadas.contar_presentes_por_chamada", return_value=20):
        resposta = status_chamada(str(TURMA_ID), current_user=ADMIN)

    assert resposta["ausentes"] == 7
    assert_resposta_conforme(resposta, "GET", "/chamadas/status/{turma_id}")


def test_status_sem_chamada_aberta_conforme():
    """Sem chamada aberta a resposta é MENOR: só `status` e os contadores
    zerados, sem `chamada_id` nem `horario_inicio`. São dois formatos, e é por
    isso que o modelo declarado é a união dos dois."""
    from routers.chamadas import status_chamada

    with patch("routers.chamadas.obter_chamada_aberta_por_turma", return_value=None):
        resposta = status_chamada(str(TURMA_ID), current_user=ADMIN)

    assert "chamada_id" not in resposta
    assert_resposta_conforme(resposta, "GET", "/chamadas/status/{turma_id}")


def test_alunos_da_chamada_conforme():
    from routers.chamadas import listar_alunos_chamada

    alunos = [
        {"id": ALUNO_ID, "nome": "Bruno Lima", "total_aulas": 2, "aulas_presentes": [1, 2]},
        # Ausente vem na lista com `aulas_presentes` vazio — a tela de revisão
        # precisa da linha dele para permitir o ajuste manual.
        {"id": uuid.UUID("9d8c7b6a-5e4f-4312-8a90-1b2c3d4e5f60"),
         "nome": "Carla Souza", "total_aulas": 2, "aulas_presentes": []},
    ]
    with patch("routers.chamadas.obter_chamada_por_id",
               return_value={"chamada_id": 41, "turma_id": str(TURMA_ID), "total_aulas": 2}), \
         patch("routers.chamadas.listar_alunos_da_chamada", return_value=alunos):
        resposta = listar_alunos_chamada("41", current_user=ADMIN)

    assert resposta["total_aulas"] == 2
    assert resposta["alunos"][1]["aulas_presentes"] == []
    assert_resposta_conforme(resposta, "GET", "/chamadas/{chamada_id}/alunos")


def test_alunos_da_chamada_sem_alunos_conforme():
    """Chamada de turma sem matrícula: `total_aulas` cai para o valor da própria
    chamada, porque não há primeira linha de onde tirá-lo."""
    from routers.chamadas import listar_alunos_chamada

    with patch("routers.chamadas.obter_chamada_por_id",
               return_value={"chamada_id": 41, "turma_id": str(TURMA_ID), "total_aulas": 3}), \
         patch("routers.chamadas.listar_alunos_da_chamada", return_value=[]):
        resposta = listar_alunos_chamada("41", current_user=ADMIN)

    assert resposta == {"total_aulas": 3, "alunos": []}
    assert_resposta_conforme(resposta, "GET", "/chamadas/{chamada_id}/alunos")


# --------------------------------------------------------------------------
# auth — a confirmação de sessão
# --------------------------------------------------------------------------
def _pedido_real():
    """`Request` de verdade, não `MagicMock`: a rota tem `@limiter.limit` e o
    slowapi rejeita qualquer outra coisa ("parameter `request` must be an
    instance of starlette.requests.Request"). O storage do limiter já é o de
    memória, pela fixture de sessão do conftest."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/session",
            "headers": [],
            "query_string": b"",
            "client": ("203.0.113.7", 45678),
        }
    )


def test_sessao_valida_conforme():
    """Nada é consultado no banco: os três campos saem do próprio token."""
    from routers.auth import validar_sessao

    pedido = _pedido_real()
    resposta = validar_sessao(
        request=pedido,
        current_user={"sub": ALUNO_USUARIO_ID, "email": "bruno@escola.local", "role": "Aluno"},
    )

    assert resposta["usuario_id"] == ALUNO_USUARIO_ID
    assert_resposta_conforme(resposta, "GET", "/auth/session")


def test_sessao_valida_sem_email_conforme():
    """Token sem a claim `email` devolve `null` — o campo vem de `.get()`, não
    de consulta, e nenhum caminho o preenche depois."""
    from routers.auth import validar_sessao

    resposta = validar_sessao(
        request=_pedido_real(),
        current_user={"sub": ALUNO_USUARIO_ID, "role": "Aluno"},
    )

    assert resposta["email"] is None
    assert_resposta_conforme(resposta, "GET", "/auth/session")
