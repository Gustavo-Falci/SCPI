"""Contadores de `listar_relatorios_chamadas` contra Postgres real.

Gate SCPI_RUN_DB_TESTS=1 (service postgres:16 do CI). Existe porque o resto da
suíte de relatórios usa cursor mockado, que não parseia SQL: a troca dos quatro
subselects correlacionados pelo LATERAL passaria verde mesmo devolvendo número
errado. Aqui os números são conferidos de verdade.

O cenário tem um aluno DESMATRICULADO com presença registrada — é o caso que
separa `presentes` (linhas de Presencas da chamada) de `total_alunos` (linhas de
Turma_Alunos). Dobrar `presentes` para dentro do LATERAL o perderia em silêncio.
"""
import uuid

import pytest

from infra.database import get_db_cursor


@pytest.fixture
def cenario_relatorio(pg):
    """Chamada fechada de 2 aulas com um aluno de cada situação.

    presente (2 de 2), parcial (1 de 2), ausente (0 de 2) e um ex-aluno com 1
    presença que já saiu da turma.
    """
    from infra.migrations import _apply_all

    _apply_all()

    marca = uuid.uuid4().hex[:8]
    ids = {chave: str(uuid.uuid4())
           for chave in ("turma", "professor", "presente", "parcial", "ausente", "ex")}

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO Turmas (turma_id, codigo_turma, nome_disciplina, "
            "periodo_letivo, turno, semestre) "
            "VALUES (%s, %s, 'Cálculo I', '2026/1', 'Matutino', '3')",
            (ids["turma"], f"REL-{marca}"),
        )

        usuario_prof = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario) "
            "VALUES (%s, 'Ana Souza', %s, 'x', 'Professor')",
            (usuario_prof, f"prof-{marca}@teste.local"),
        )
        cur.execute(
            "INSERT INTO Professores (professor_id, usuario_id) VALUES (%s, %s)",
            (ids["professor"], usuario_prof),
        )
        ids["usuarios"] = [usuario_prof]

        for chave in ("presente", "parcial", "ausente", "ex"):
            usuario_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario) "
                "VALUES (%s, %s, %s, 'x', 'Aluno')",
                (usuario_id, f"Aluno {chave}", f"{chave}-{marca}@teste.local"),
            )
            cur.execute(
                "INSERT INTO Alunos (aluno_id, usuario_id, ra, turno) "
                "VALUES (%s, %s, %s, 'Matutino')",
                (ids[chave], usuario_id, f"RA-{chave}-{marca}"),
            )
            ids["usuarios"].append(usuario_id)

        # "ex" fica de fora: teve presença na aula e depois saiu da turma.
        cur.execute(
            "INSERT INTO Turma_Alunos (turma_id, aluno_id) VALUES (%s, %s), (%s, %s), (%s, %s)",
            (ids["turma"], ids["presente"], ids["turma"], ids["parcial"],
             ids["turma"], ids["ausente"]),
        )

        cur.execute(
            "INSERT INTO Chamadas (turma_id, professor_id, data_chamada, horario_inicio, "
            "horario_fim, status, total_aulas) "
            "VALUES (%s, %s, DATE '2026-05-10', TIME '08:00', TIME '09:40', 'Fechada', 2) "
            "RETURNING chamada_id",
            (ids["turma"], ids["professor"]),
        )
        ids["chamada"] = cur.fetchone()["chamada_id"]

        for aluno, aulas in [("presente", (1, 2)), ("parcial", (1,)), ("ex", (1,))]:
            for num_aula in aulas:
                cur.execute(
                    "INSERT INTO Presencas (chamada_id, aluno_id, num_aula) "
                    "VALUES (%s, %s, %s)",
                    (ids["chamada"], ids[aluno], num_aula),
                )

    yield ids

    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM Usuarios WHERE usuario_id = ANY(%s::uuid[])",
                    (ids["usuarios"],))
        cur.execute("DELETE FROM Turmas WHERE turma_id = %s::uuid", (ids["turma"],))


def _linha(cenario):
    from repositories.chamadas import listar_relatorios_chamadas

    linhas = listar_relatorios_chamadas(professor_id=cenario["professor"])
    assert len(linhas) == 1, "o recorte por professor deveria isolar a chamada do cenário"
    return linhas[0]


def test_total_alunos_conta_so_os_matriculados(cenario_relatorio):
    assert _linha(cenario_relatorio)["total_alunos"] == 3


def test_presentes_conta_slots_inclusive_de_ex_aluno(cenario_relatorio):
    """2 (presente) + 1 (parcial) + 1 (ex-aluno) = 4 linhas de Presencas."""
    assert _linha(cenario_relatorio)["presentes"] == 4


def test_situacoes_por_aluno_somam_o_total_da_turma(cenario_relatorio):
    linha = _linha(cenario_relatorio)
    assert linha["presentes_alunos"] == 1
    assert linha["parciais_alunos"] == 1
    assert linha["ausentes_alunos"] == 1
    assert (linha["presentes_alunos"] + linha["parciais_alunos"]
            + linha["ausentes_alunos"]) == linha["total_alunos"]


def test_percentual_do_service_usa_slots_e_nao_alunos(cenario_relatorio):
    """4 presenças em 3 alunos × 2 aulas = 67%; ausentes = 6 - 4."""
    from services.relatorios import listar_relatorios

    item = listar_relatorios(professor_id=cenario_relatorio["professor"])[0]
    assert item["percentual"] == 67
    assert item["ausentes"] == 2


def test_turma_sem_alunos_devolve_zeros_e_nao_some_da_lista(cenario_relatorio):
    """LEFT JOIN LATERAL ... ON true: chamada de turma vazia continua listada."""
    from repositories.chamadas import listar_relatorios_chamadas

    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM Turma_Alunos WHERE turma_id = %s::uuid",
                    (cenario_relatorio["turma"],))

    linha = listar_relatorios_chamadas(professor_id=cenario_relatorio["professor"])[0]
    assert linha["total_alunos"] == 0
    assert linha["presentes_alunos"] == 0
    assert linha["parciais_alunos"] == 0
    assert linha["ausentes_alunos"] == 0
