"""Testes da frequência por aluno (repo/service/router) — sem DB real."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def _mock_cursor(fetchall_return=None, fetchone_return=None):
    cur = MagicMock()
    cur.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    cur.fetchone.return_value = fetchone_return
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return cm, cur


def test_repo_aplica_filtro_de_datas():
    cm, cur = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_frequencia_turma
        listar_frequencia_turma("t1", data_inicio="2026-03-01", data_fim="2026-07-22")
    sql, params = cur.execute.call_args[0]
    assert "c.data_chamada >= %s" in sql
    assert "c.data_chamada <= %s" in sql
    assert "c.status = 'Fechada'" in sql
    assert params == ("t1", "2026-03-01", "2026-07-22", "t1")


def test_repo_sem_datas_nao_adiciona_clausulas():
    cm, cur = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_frequencia_turma
        listar_frequencia_turma("t1")
    sql, params = cur.execute.call_args[0]
    assert "c.data_chamada >= %s" not in sql
    assert params == ("t1", "t1")


def test_repo_denominador_por_aluno_usa_data_associacao():
    """aulas_dadas/chamadas_count contam só chamadas a partir da matrícula do aluno."""
    cm, cur = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_frequencia_turma
        listar_frequencia_turma("t1")
    sql, _ = cur.execute.call_args[0]
    # comparação por data (não timestamp) evita off-by-one no mesmo dia
    assert "ta.data_associacao::date" in sql
    # colunas turma-level (sem filtro por aluno) para o cabeçalho do relatório
    assert "aulas_dadas_periodo" in sql
    assert "chamadas_periodo_count" in sql


def test_repo_numerador_usa_mesma_janela_do_denominador():
    """As presenças contadas (numerador) precisam vir só das chamadas pós-matrícula.

    Se o numerador contar presenças de chamadas anteriores à matrícula enquanto o
    denominador (aulas_dadas) as exclui, a frequência pode passar de 100%.
    """
    import re
    cm, cur = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_frequencia_turma
        listar_frequencia_turma("t1")
    sql, _ = cur.execute.call_args[0]
    compact = re.sub(r"\s+", " ", sql)
    assert (
        "p.chamada_id IN (SELECT cp.chamada_id FROM chamadas_periodo cp "
        "WHERE cp.data_chamada >= ta.data_associacao::date)"
    ) in compact


# aulas_dadas/chamadas_count = por-aluno (pós-matrícula); *_periodo = turma-level.
# Aqui todos entraram no início, então por-aluno == turma-level.
ALUNOS = [
    {"aluno_id": "a1", "nome": "Ana", "ra": "1", "aulas_presentes": 8, "aulas_dadas": 10,
     "chamadas_count": 5, "aulas_dadas_periodo": 10, "chamadas_periodo_count": 5},
    {"aluno_id": "a2", "nome": "Bruno", "ra": "2", "aulas_presentes": 5, "aulas_dadas": 10,
     "chamadas_count": 5, "aulas_dadas_periodo": 10, "chamadas_periodo_count": 5},
    {"aluno_id": "a3", "nome": "Carla", "ra": "3", "aulas_presentes": 0, "aulas_dadas": 10,
     "chamadas_count": 5, "aulas_dadas_periodo": 10, "chamadas_periodo_count": 5},
]
TURMA = {"turma_id": "t1", "nome_disciplina": "Cálculo I", "codigo_turma": "TURMA-3B",
         "turno": "Noturno", "semestre": "2026.1", "professor_nome": "Ana Souza"}


def test_service_calcula_percentual_e_situacao():
    with patch("services.relatorios.listar_frequencia_turma", return_value=ALUNOS), \
         patch("services.relatorios.obter_turma_relatorio", return_value=TURMA):
        from services.relatorios import frequencia_turma
        out = frequencia_turma("t1")
    por_id = {a["aluno_id"]: a for a in out["alunos"]}
    assert por_id["a1"]["percentual"] == 80
    assert por_id["a1"]["situacao"] == "Regular"
    assert por_id["a2"]["percentual"] == 50
    assert por_id["a2"]["situacao"] == "Risco"
    assert por_id["a3"]["percentual"] == 0


def test_service_ordena_por_frequencia_crescente():
    with patch("services.relatorios.listar_frequencia_turma", return_value=ALUNOS), \
         patch("services.relatorios.obter_turma_relatorio", return_value=TURMA):
        from services.relatorios import frequencia_turma
        out = frequencia_turma("t1")
    assert [a["aluno_id"] for a in out["alunos"]] == ["a3", "a2", "a1"]


def test_service_totais_do_periodo():
    with patch("services.relatorios.listar_frequencia_turma", return_value=ALUNOS), \
         patch("services.relatorios.obter_turma_relatorio", return_value=TURMA):
        from services.relatorios import frequencia_turma
        out = frequencia_turma("t1")
    assert out["totais"]["total_alunos"] == 3
    assert out["totais"]["aulas_dadas"] == 10
    assert out["totais"]["chamadas"] == 5
    assert out["totais"]["percentual"] == 43  # (8+5+0) / 30


def test_service_denominador_por_aluno_matricula_tardia():
    """Aluno que entrou tarde é medido pelo próprio denominador, não pelo da turma."""
    linhas = [
        # entrou no início: 5 de 10
        {"aluno_id": "a1", "nome": "Ana", "ra": "1", "aulas_presentes": 5, "aulas_dadas": 10,
         "chamadas_count": 5, "aulas_dadas_periodo": 10, "chamadas_periodo_count": 5},
        # entrou no meio: 3 de 4 (não 3 de 10) → Regular, não Risco
        {"aluno_id": "a2", "nome": "Bruno", "ra": "2", "aulas_presentes": 3, "aulas_dadas": 4,
         "chamadas_count": 2, "aulas_dadas_periodo": 10, "chamadas_periodo_count": 5},
    ]
    with patch("services.relatorios.listar_frequencia_turma", return_value=linhas), \
         patch("services.relatorios.obter_turma_relatorio", return_value=TURMA):
        from services.relatorios import frequencia_turma
        out = frequencia_turma("t1")
    por_id = {a["aluno_id"]: a for a in out["alunos"]}
    assert por_id["a2"]["percentual"] == 75
    assert por_id["a2"]["situacao"] == "Regular"


def test_service_aluno_sem_aula_apos_matricula_e_insuficiente():
    """Aluno matriculado após a última chamada não tem denominador → não é 'Risco'."""
    linhas = [
        {"aluno_id": "a1", "nome": "Ana", "ra": "1", "aulas_presentes": 0, "aulas_dadas": 0,
         "chamadas_count": 0, "aulas_dadas_periodo": 10, "chamadas_periodo_count": 5},
    ]
    with patch("services.relatorios.listar_frequencia_turma", return_value=linhas), \
         patch("services.relatorios.obter_turma_relatorio", return_value=TURMA):
        from services.relatorios import frequencia_turma
        out = frequencia_turma("t1")
    aluno = out["alunos"][0]
    assert aluno["situacao"] == "Insuficiente"
    assert aluno["situacao"] != "Risco"
    assert aluno["percentual"] == 0


def test_service_totais_somam_denominador_por_aluno():
    """Percentual da turma = presenças / soma dos denominadores por aluno; header = turma-level."""
    linhas = [
        {"aluno_id": "a1", "nome": "Ana", "ra": "1", "aulas_presentes": 5, "aulas_dadas": 10,
         "chamadas_count": 5, "aulas_dadas_periodo": 10, "chamadas_periodo_count": 5},
        {"aluno_id": "a2", "nome": "Bruno", "ra": "2", "aulas_presentes": 3, "aulas_dadas": 4,
         "chamadas_count": 2, "aulas_dadas_periodo": 10, "chamadas_periodo_count": 5},
    ]
    with patch("services.relatorios.listar_frequencia_turma", return_value=linhas), \
         patch("services.relatorios.obter_turma_relatorio", return_value=TURMA):
        from services.relatorios import frequencia_turma
        out = frequencia_turma("t1")
    # header mostra as aulas dadas da turma (turma-level), não a soma por aluno
    assert out["totais"]["aulas_dadas"] == 10
    assert out["totais"]["chamadas"] == 5
    # percentual = (5+3) / (10+4) = 8/14 ≈ 57
    assert out["totais"]["percentual"] == 57


def test_service_turma_sem_chamadas_nao_divide_por_zero():
    vazio = [{"aluno_id": "a1", "nome": "Ana", "ra": "1", "aulas_presentes": 0,
              "aulas_dadas": 0, "chamadas_count": 0,
              "aulas_dadas_periodo": 0, "chamadas_periodo_count": 0}]
    with patch("services.relatorios.listar_frequencia_turma", return_value=vazio), \
         patch("services.relatorios.obter_turma_relatorio", return_value=TURMA):
        from services.relatorios import frequencia_turma
        out = frequencia_turma("t1")
    assert out["alunos"][0]["percentual"] == 0
    assert out["totais"]["percentual"] == 0


def test_service_turma_inexistente_404():
    with patch("services.relatorios.obter_turma_relatorio", return_value=None):
        from services.relatorios import frequencia_turma
        with pytest.raises(HTTPException) as exc:
            frequencia_turma("t-inexistente")
    assert exc.value.status_code == 404


def test_service_professor_de_outra_turma_recebe_404():
    with patch("services.relatorios.obter_turma_relatorio", return_value=TURMA), \
         patch("services.relatorios.professor_responsavel_pela_turma", return_value=False):
        from services.relatorios import frequencia_turma
        with pytest.raises(HTTPException) as exc:
            frequencia_turma("t1", professor_id="p-outro")
    assert exc.value.status_code == 404


def test_router_professor_repassa_professor_id():
    from routers.relatorios import frequencia_turma_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.frequencia_turma", return_value={"alunos": []}) as m:
        frequencia_turma_professor(
            turma_id="t1", current_user={"sub": "u1", "role": "Professor"}
        )
    assert m.call_args.kwargs["professor_id"] == "p1"


def test_router_admin_nao_filtra_por_professor():
    from routers.relatorios import frequencia_turma_admin

    with patch("routers.relatorios.frequencia_turma", return_value={"alunos": []}) as m:
        frequencia_turma_admin(turma_id="t1", current_user={"sub": "u1", "role": "Admin"})
    assert m.call_args.kwargs.get("professor_id") is None


def test_router_range_de_datas_invertido_retorna_400():
    from datetime import date

    from routers.relatorios import frequencia_turma_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"):
        with pytest.raises(HTTPException) as exc:
            frequencia_turma_professor(
                turma_id="t1",
                data_inicio=date(2026, 7, 22),
                data_fim=date(2026, 3, 1),
                current_user={"sub": "u1", "role": "Professor"},
            )
    assert exc.value.status_code == 400
