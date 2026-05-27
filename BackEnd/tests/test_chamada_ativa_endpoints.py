"""Testes de mapeamento de chamada aberta nos routers de leitura (sem DB)."""
from unittest.mock import patch


def _row_base():
    return {
        "prof_nome": "Prof X",
        "chamada_id": 10, "turma_id": "T1", "total_aulas": 2,
        "nome_disciplina": "Matematica",
        "total": 5, "presentes": 3, "parciais": 1, "ausentes": 1,
    }


def test_dashboard_expoe_chamada_ativa():
    from routers.professores import get_dashboard
    row = _row_base() | {
        "aberta_chamada_id": 10, "aberta_turma_id": "T1", "aberta_turma_nome": "Matematica",
    }
    with patch("routers.professores.obter_dashboard_professor", return_value=row), \
         patch("routers.professores.listar_aulas_hoje_por_professor", return_value=[]):
        resp = get_dashboard(usuario_id="u1", current_user={"sub": "u1", "role": "Professor"})
    assert resp["chamada_ativa"] == {
        "chamada_id": 10, "turma_id": "T1", "turma_nome": "Matematica",
    }


def test_dashboard_sem_chamada_ativa_retorna_none():
    from routers.professores import get_dashboard
    row = _row_base() | {
        "aberta_chamada_id": None, "aberta_turma_id": None, "aberta_turma_nome": None,
    }
    with patch("routers.professores.obter_dashboard_professor", return_value=row), \
         patch("routers.professores.listar_aulas_hoje_por_professor", return_value=[]):
        resp = get_dashboard(usuario_id="u1", current_user={"sub": "u1", "role": "Professor"})
    assert resp["chamada_ativa"] is None


def test_turmas_marca_chamada_aberta():
    from routers.turmas import get_turmas
    rows = [{
        "turma_id": "T1", "nome_disciplina": "Matematica", "codigo_turma": "C1",
        "dia_semana": None, "horario_inicio": None, "horario_fim": None,
        "chamada_aberta_id": 99,
    }]
    with patch("routers.turmas.listar_turmas_com_horarios_por_professor", return_value=rows):
        resp = get_turmas(usuario_id="u1", current_user={"sub": "u1", "role": "Professor"})
    t = resp["turmas"][0]
    assert t["chamada_aberta"] is True
    assert t["chamada_id"] == 99


def test_turmas_sem_chamada_aberta():
    from routers.turmas import get_turmas
    rows = [{
        "turma_id": "T1", "nome_disciplina": "Matematica", "codigo_turma": "C1",
        "dia_semana": None, "horario_inicio": None, "horario_fim": None,
        "chamada_aberta_id": None,
    }]
    with patch("routers.turmas.listar_turmas_com_horarios_por_professor", return_value=rows):
        resp = get_turmas(usuario_id="u1", current_user={"sub": "u1", "role": "Professor"})
    t = resp["turmas"][0]
    assert t["chamada_aberta"] is False
    assert t["chamada_id"] is None
