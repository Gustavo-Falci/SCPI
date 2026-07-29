"""Testes da listagem filtrada de alunos para o admin — sem DB real."""
from unittest.mock import MagicMock, patch


def _mock_cursor(fetchall_return=None):
    """Retorna (context_manager, cursor) para patchar get_db_cursor."""
    cur = MagicMock()
    cur.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return cm, cur


def _chamar(**kwargs):
    """Executa listar_alunos_para_admin com cursor mockado e devolve (resultado, sql, params)."""
    linha = {
        "aluno_id": "a1", "ra": "2024001", "nome": "Maria Santos",
        "email": "maria@escola.com", "turno": "Matutino",
        "turmas_count": 2, "tem_biometria": True, "ja_matriculado": False,
        "total_geral": 1,
    }
    cm, cur = _mock_cursor(fetchall_return=[linha])
    with patch("repositories.alunos.get_db_cursor", return_value=cm):
        from repositories.alunos import listar_alunos_para_admin
        resultado = listar_alunos_para_admin(**kwargs)
    sql, params = cur.execute.call_args[0]
    return resultado, sql, params


def test_sem_filtros_retorna_envelope_com_total():
    resultado, sql, params = _chamar()
    assert resultado["items"][0]["nome"] == "Maria Santos"
    assert resultado["total"] == 1
    # total_geral é detalhe interno da query e não deve vazar para o item
    assert "total_geral" not in resultado["items"][0]
    assert "LIMIT" in sql.upper()
    assert params[-2:] == [10, 0]


def test_busca_textual_usa_parametro_e_nao_percent_literal():
    _resultado, sql, params = _chamar(q="maria")
    assert "%maria%" in params
    assert params.count("%maria%") == 3  # nome, email, ra
    # O curinga vive no parâmetro; fora dos placeholders o SQL não pode ter '%'.
    assert "%" not in sql.replace("%s", "")


def test_turno_vira_predicado_com_parametro():
    _resultado, sql, params = _chamar(turno="Noturno")
    assert "a.turno = %s" in sql
    assert "Noturno" in params


def test_semestre_usa_exists_em_turma_alunos():
    _resultado, sql, params = _chamar(semestre="3")
    assert "EXISTS" in sql
    assert "Turma_Alunos" in sql
    assert "t.semestre = %s" in sql
    assert "3" in params


def test_periodo_letivo_e_turma_combinam_no_mesmo_exists():
    _resultado, sql, params = _chamar(periodo_letivo="2026/1", turma_id="t1")
    assert sql.count("EXISTS (SELECT 1 FROM Turma_Alunos") == 1
    assert "t.periodo_letivo = %s" in sql
    assert "ta.turma_id = %s" in sql
    assert "2026/1" in params and "t1" in params


def test_situacao_sem_turma_usa_not_exists():
    _resultado, sql, _params = _chamar(situacao="sem_turma")
    assert "NOT EXISTS (SELECT 1 FROM Turma_Alunos" in sql


def test_situacao_sem_biometria_ignora_rosto_revogado():
    _resultado, sql, _params = _chamar(situacao="sem_biometria")
    assert "NOT EXISTS (SELECT 1 FROM Colecao_Rostos" in sql
    assert "revogado_em IS NULL" in sql


def test_contexto_turma_id_liga_ja_matriculado():
    _resultado, sql, params = _chamar(contexto_turma_id="t9")
    assert "ja_matriculado" in sql
    assert "t9" in params


def test_sem_contexto_ja_matriculado_e_falso_constante():
    _resultado, sql, _params = _chamar()
    assert "FALSE as ja_matriculado" in sql


def test_paginacao_calcula_offset():
    _resultado, _sql, params = _chamar(page=3, limit=25)
    assert params[-2:] == [25, 50]


def test_limit_acima_do_teto_e_reduzido():
    _resultado, _sql, params = _chamar(limit=5000)
    assert params[-2] == 100


def test_page_invalida_cai_para_primeira():
    _resultado, _sql, params = _chamar(page=0)
    assert params[-1] == 0


def test_lista_vazia_retorna_total_zero():
    cm, _cur = _mock_cursor(fetchall_return=[])
    with patch("repositories.alunos.get_db_cursor", return_value=cm):
        from repositories.alunos import listar_alunos_para_admin
        resultado = listar_alunos_para_admin()
    assert resultado == {"items": [], "total": 0}


def test_sem_cursor_retorna_envelope_vazio():
    cm = MagicMock()
    cm.__enter__.return_value = None
    cm.__exit__.return_value = False
    with patch("repositories.alunos.get_db_cursor", return_value=cm):
        from repositories.alunos import listar_alunos_para_admin
        resultado = listar_alunos_para_admin()
    assert resultado == {"items": [], "total": 0}


def test_pendentes_com_turno_ativo_traz_turno_nulo():
    _resultado, sql, params = _chamar(situacao="pendentes", turno="Matutino")
    assert "a.turno IS NULL" in sql
    # o predicado normal de turno não pode coexistir: ele excluiria justamente os nulos
    assert "a.turno = %s" not in sql
    assert "Matutino" not in params


def test_pendentes_com_semestre_ativo_nega_o_escopo():
    _resultado, sql, params = _chamar(situacao="pendentes", semestre="3")
    assert "NOT EXISTS (SELECT 1 FROM Turma_Alunos ta" in sql
    assert "t.semestre = %s" in sql
    assert "3" in params


def test_pendentes_sem_escopo_e_turno_nulo_ou_sem_turma():
    _resultado, sql, _params = _chamar(situacao="pendentes")
    assert "a.turno IS NULL" in sql
    assert "NOT EXISTS (SELECT 1 FROM Turma_Alunos ta WHERE ta.aluno_id = a.aluno_id)" in sql
    assert " OR " in sql


def test_pendentes_preserva_busca_textual():
    _resultado, _sql, params = _chamar(situacao="pendentes", q="maria")
    assert "%maria%" in params


def _contar(**kwargs):
    cm, cur = _mock_cursor()
    cur.fetchone.return_value = {"total": 7}
    with patch("repositories.alunos.get_db_cursor", return_value=cm):
        from repositories.alunos import contar_alunos_pendentes
        total = contar_alunos_pendentes(**kwargs)
    sql, params = cur.execute.call_args[0]
    return total, sql, params


def test_contar_pendentes_sem_escopo_retorna_zero_sem_consultar():
    cm, cur = _mock_cursor()
    with patch("repositories.alunos.get_db_cursor", return_value=cm):
        from repositories.alunos import contar_alunos_pendentes
        assert contar_alunos_pendentes() == 0
    cur.execute.assert_not_called()


def test_contar_pendentes_com_escopo_consulta_e_retorna_total():
    total, sql, params = _contar(turno="Matutino", semestre="3")
    assert total == 7
    assert "COUNT(*)" in sql
    assert "a.turno IS NULL" in sql
    assert "3" in params
