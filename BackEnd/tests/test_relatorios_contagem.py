"""Contagem de chamadas para a paginação (sem DB real)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from repositories.chamadas import contar_relatorios_chamadas


def _mock_cursor(total=7):
    cur = MagicMock()
    cur.fetchone.return_value = {"total": total}

    @contextmanager
    def fake_cursor(commit=False):
        yield cur

    return cur, fake_cursor


def test_devolve_total_do_count():
    _, fake = _mock_cursor(total=123)
    with patch("repositories.chamadas.get_db_cursor", fake):
        assert contar_relatorios_chamadas(professor_id="p1") == 123


def test_sem_cursor_retorna_zero():
    @contextmanager
    def sem_cursor(commit=False):
        yield None

    with patch("repositories.chamadas.get_db_cursor", sem_cursor):
        assert contar_relatorios_chamadas(professor_id="p1") == 0


def test_conta_so_chamadas_fechadas():
    cur, fake = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", fake):
        contar_relatorios_chamadas(professor_id="p1")
    sql = cur.execute.call_args[0][0]
    assert "COUNT(*)" in sql
    assert "c.status = 'Fechada'" in sql


def test_nao_carrega_os_subselects_da_listagem():
    # Os 5 subselects correlacionados existem para montar o card; contar não
    # precisa deles e pagá-los por linha seria desperdício.
    cur, fake = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", fake):
        contar_relatorios_chamadas(professor_id="p1")
    sql = cur.execute.call_args[0][0]
    assert "presentes_alunos" not in sql
    assert "Turma_Alunos" not in sql


def test_aplica_todos_os_filtros():
    cur, fake = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", fake):
        contar_relatorios_chamadas(
            professor_id="p1", turma_id="t1", data_inicio="2026-01-01",
            data_fim="2026-06-30", turno="Matutino", semestre="3",
        )
    sql, params = cur.execute.call_args[0]
    assert "c.professor_id = %s" in sql
    assert "c.turma_id = %s" in sql
    assert "c.data_chamada >= %s" in sql
    assert "c.data_chamada <= %s" in sql
    assert "t.turno = %s" in sql
    assert "t.semestre = %s" in sql
    assert params == ("p1", "t1", "2026-01-01", "2026-06-30", "Matutino", "3")


def test_sem_filtros_nao_adiciona_where_extra():
    cur, fake = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", fake):
        contar_relatorios_chamadas()
    sql, params = cur.execute.call_args[0]
    assert "c.professor_id" not in sql
    assert params == ()


def test_servico_nao_aceita_frequencia_baixa():
    # frequencia_baixa filtra em Python depois do SQL (services/relatorios.py:46);
    # aceitá-lo aqui devolveria um total que não bate com a lista.
    import inspect

    from services.relatorios import contar_relatorios

    assert "frequencia_baixa" not in inspect.signature(contar_relatorios).parameters
