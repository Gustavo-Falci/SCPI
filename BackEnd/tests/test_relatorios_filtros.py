"""Testes dos filtros de relatórios (repo/service/router) — sem DB real."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def _mock_cursor(fetchall_return=None):
    """Retorna (context_manager, cursor) para patchar get_db_cursor."""
    cur = MagicMock()
    cur.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return cm, cur


def test_listar_relatorios_chamadas_aplica_todos_os_filtros():
    cm, cur = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_relatorios_chamadas
        listar_relatorios_chamadas(
            professor_id="p1",
            data_inicio="2026-05-01",
            data_fim="2026-05-31",
            turno="Matutino",
            semestre="2026.1",
        )
    sql, params = cur.execute.call_args[0]
    assert "c.data_chamada >= %s" in sql
    assert "c.data_chamada <= %s" in sql
    assert "t.turno = %s" in sql
    assert "t.semestre = %s" in sql
    assert params == ("p1", "2026-05-01", "2026-05-31", "Matutino", "2026.1", 200, 0)


def test_listar_relatorios_chamadas_sem_filtros_nao_adiciona_clausulas():
    cm, cur = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_relatorios_chamadas
        listar_relatorios_chamadas(professor_id="p1")
    sql, params = cur.execute.call_args[0]
    assert "c.data_chamada >= %s" not in sql
    assert "c.data_chamada <= %s" not in sql
    assert "t.turno = %s" not in sql
    assert "t.semestre = %s" not in sql
    assert params == ("p1", 200, 0)


def test_listar_relatorios_agrega_situacoes_num_unico_lateral():
    """Os 3 subselects que repetiam o mesmo join viraram um LATERAL.

    Asserção sobre a forma do SQL porque o cursor aqui é mock e não executa
    nada; os números estão pinados em test_relatorios_lateral_db.py.
    """
    cm, cur = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_relatorios_chamadas
        listar_relatorios_chamadas(professor_id="p1")
    sql = cur.execute.call_args[0][0]
    assert "LEFT JOIN LATERAL" in sql
    assert sql.count("FROM Turma_Alunos ta") == 1


def test_listar_relatorios_mantem_presentes_fora_do_lateral():
    """`presentes` conta Presencas da chamada, inclusive de quem saiu da turma.

    O LATERAL parte de Turma_Alunos e perderia essas linhas.
    """
    cm, cur = _mock_cursor()
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_relatorios_chamadas
        listar_relatorios_chamadas(professor_id="p1")
    sql = cur.execute.call_args[0][0]
    assert "FROM Presencas p  WHERE p.chamada_id  = c.chamada_id) AS presentes" in sql


def test_listar_opcoes_filtros_relatorios_deriva_distintos():
    # professor_id/professor_nome entraram no SELECT junto com o filtro de
    # professor do admin; a query real devolve as duas colunas.
    rows = [
        {"turma_id": "T1", "nome_disciplina": "Calculo", "codigo_turma": "C1",
         "turno": "Matutino", "semestre": "2026.1",
         "professor_id": "p1", "professor_nome": "Ana"},
        {"turma_id": "T2", "nome_disciplina": "Fisica", "codigo_turma": "C2",
         "turno": "Noturno", "semestre": "2025.2",
         "professor_id": "p1", "professor_nome": "Ana"},
    ]
    cm, cur = _mock_cursor(fetchall_return=rows)
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_opcoes_filtros_relatorios
        out = listar_opcoes_filtros_relatorios("p1")
    sql, params = cur.execute.call_args[0]
    assert "c.status = 'Fechada'" in sql
    assert "c.professor_id = %s" in sql
    assert params == ("p1",)
    assert [t["turma_id"] for t in out["turmas"]] == ["T1", "T2"]
    assert out["turnos"] == ["Matutino", "Noturno"]
    assert out["semestres"] == ["2026.1", "2025.2"]
    assert out["turmas"][0] == {
        "turma_id": "T1", "nome_disciplina": "Calculo", "codigo_turma": "C1"
    }


def test_service_listar_relatorios_repassa_filtros():
    with patch("services.relatorios.listar_relatorios_chamadas", return_value=[]) as m:
        from services.relatorios import listar_relatorios
        listar_relatorios(
            professor_id="p1",
            data_inicio="2026-05-01",
            data_fim="2026-05-31",
            turno="Matutino",
            semestre="2026.1",
        )
    kwargs = m.call_args.kwargs
    assert kwargs["data_inicio"] == "2026-05-01"
    assert kwargs["data_fim"] == "2026-05-31"
    assert kwargs["turno"] == "Matutino"
    assert kwargs["semestre"] == "2026.1"


def test_service_opcoes_filtros_delega_ao_repo():
    esperado = {"turmas": [], "turnos": [], "semestres": []}
    with patch("services.relatorios.listar_opcoes_filtros_relatorios",
               return_value=esperado) as m:
        from services.relatorios import opcoes_filtros_relatorios
        out = opcoes_filtros_relatorios("p1")
    m.assert_called_once_with("p1")
    assert out == esperado


def test_router_range_invertido_retorna_400():
    from routers.relatorios import listar_relatorios_professor
    with patch("routers.relatorios.obter_professor_id", return_value="p1"):
        with pytest.raises(HTTPException) as exc:
            listar_relatorios_professor(
                data_inicio=date(2026, 5, 31),
                data_fim=date(2026, 5, 1),
                current_user={"sub": "u1", "role": "Professor"},
            )
    assert exc.value.status_code == 400


def test_router_turno_invalido_retorna_400():
    from routers.relatorios import listar_relatorios_professor
    with patch("routers.relatorios.obter_professor_id", return_value="p1"):
        with pytest.raises(HTTPException) as exc:
            listar_relatorios_professor(
                turno="Vespertino",
                current_user={"sub": "u1", "role": "Professor"},
            )
    assert exc.value.status_code == 400


def test_router_repassa_filtros_ao_service():
    from routers.relatorios import listar_relatorios_professor
    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.listar_relatorios", return_value=[]) as m:
        listar_relatorios_professor(
            turma_id="T1",
            turno="Matutino",
            semestre="2026.1",
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 5, 31),
            current_user={"sub": "u1", "role": "Professor"},
        )
    kwargs = m.call_args.kwargs
    assert kwargs["turma_id"] == "T1"
    assert kwargs["turno"] == "Matutino"
    assert kwargs["semestre"] == "2026.1"
    assert kwargs["data_inicio"] == date(2026, 5, 1)
    assert kwargs["data_fim"] == date(2026, 5, 31)


def test_router_endpoint_filtros_retorna_opcoes():
    esperado = {"turmas": [{"turma_id": "T1", "nome_disciplina": "Calculo",
                            "codigo_turma": "C1"}],
                "turnos": ["Matutino"], "semestres": ["2026.1"]}
    from routers.relatorios import opcoes_filtros_relatorios_professor
    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.opcoes_filtros_relatorios", return_value=esperado) as m:
        out = opcoes_filtros_relatorios_professor(
            current_user={"sub": "u1", "role": "Professor"}
        )
    m.assert_called_once_with("p1")
    assert out == esperado


def _linhas_opcoes():
    return [
        {"turma_id": "t1", "nome_disciplina": "Cálculo I", "codigo_turma": "MAT-101",
         "turno": "Matutino", "semestre": "3", "professor_id": "p1", "professor_nome": "Ana"},
        {"turma_id": "t1", "nome_disciplina": "Cálculo I", "codigo_turma": "MAT-101",
         "turno": "Matutino", "semestre": "3", "professor_id": "p2", "professor_nome": "Bruno"},
        {"turma_id": "t2", "nome_disciplina": "Física", "codigo_turma": "FIS-201",
         "turno": "Noturno", "semestre": "5", "professor_id": "p1", "professor_nome": "Ana"},
    ]


def test_opcoes_sem_professor_id_nao_filtra_por_professor():
    cm, cur = _mock_cursor(fetchall_return=[])
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_opcoes_filtros_relatorios
        listar_opcoes_filtros_relatorios()
    sql, params = cur.execute.call_args[0]
    assert "c.professor_id = %s" not in sql
    assert params == ()


def test_opcoes_com_professor_id_mantem_o_recorte():
    """Regressão da tela do professor, que depende deste comportamento."""
    cm, cur = _mock_cursor(fetchall_return=[])
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_opcoes_filtros_relatorios
        listar_opcoes_filtros_relatorios("p1")
    sql, params = cur.execute.call_args[0]
    assert "c.professor_id = %s" in sql
    assert params == ("p1",)


def test_opcoes_deduplica_turma_com_dois_professores():
    """Trazer o professor na query multiplica as linhas por turma."""
    cm, _cur = _mock_cursor(fetchall_return=_linhas_opcoes())
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_opcoes_filtros_relatorios
        res = listar_opcoes_filtros_relatorios()
    assert [t["turma_id"] for t in res["turmas"]] == ["t1", "t2"]


def test_opcoes_devolve_professores_sem_repeticao_ordenados():
    cm, _cur = _mock_cursor(fetchall_return=_linhas_opcoes())
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_opcoes_filtros_relatorios
        res = listar_opcoes_filtros_relatorios()
    assert res["professores"] == [
        {"professor_id": "p1", "nome": "Ana"},
        {"professor_id": "p2", "nome": "Bruno"},
    ]


def test_opcoes_mantem_turnos_e_semestres():
    cm, _cur = _mock_cursor(fetchall_return=_linhas_opcoes())
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_opcoes_filtros_relatorios
        res = listar_opcoes_filtros_relatorios()
    assert res["turnos"] == ["Matutino", "Noturno"]
    assert res["semestres"] == ["5", "3"]


def test_opcoes_sem_cursor_devolve_estrutura_vazia():
    cm = MagicMock()
    cm.__enter__.return_value = None
    cm.__exit__.return_value = False
    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import listar_opcoes_filtros_relatorios
        res = listar_opcoes_filtros_relatorios()
    assert res == {"turmas": [], "professores": [], "turnos": [], "semestres": []}


def test_rota_admin_de_filtros_nao_manda_professor_id():
    esperado = {"turmas": [], "professores": [], "turnos": [], "semestres": []}
    from routers.relatorios import opcoes_filtros_relatorios_admin
    with patch("routers.relatorios.opcoes_filtros_relatorios", return_value=esperado) as m:
        out = opcoes_filtros_relatorios_admin(current_user={"sub": "adm", "role": "Admin"})
    m.assert_called_once_with()
    assert out == esperado


def _linha_chamada(chamada_id, total_alunos, total_aulas, presentes):
    return {"chamada_id": chamada_id, "total_alunos": total_alunos,
            "total_aulas": total_aulas, "presentes": presentes}


def test_frequencia_baixa_mantem_apenas_abaixo_do_limite():
    linhas = [
        _linha_chamada("c1", 10, 1, 5),   # 50% → entra
        _linha_chamada("c2", 10, 1, 9),   # 90% → fica de fora
    ]
    with patch("services.relatorios.listar_relatorios_chamadas", return_value=linhas):
        from services.relatorios import listar_relatorios
        itens = listar_relatorios(frequencia_baixa=True)
    assert [i["chamada_id"] for i in itens] == ["c1"]


def test_exatamente_no_limite_e_regular_e_nao_entra():
    """75% é Regular no resto do sistema; o recorte é estritamente menor."""
    from core.regras import LIMITE_FREQUENCIA

    assert LIMITE_FREQUENCIA == 75
    linhas = [_linha_chamada("c1", 4, 1, 3)]  # 75%
    with patch("services.relatorios.listar_relatorios_chamadas", return_value=linhas):
        from services.relatorios import listar_relatorios
        assert listar_relatorios(frequencia_baixa=True) == []


def test_sem_o_filtro_a_lista_nao_muda():
    linhas = [_linha_chamada("c1", 10, 1, 5), _linha_chamada("c2", 10, 1, 9)]
    with patch("services.relatorios.listar_relatorios_chamadas", return_value=linhas):
        from services.relatorios import listar_relatorios
        assert len(listar_relatorios()) == 2


def test_filtro_sobre_lista_vazia_nao_quebra():
    with patch("services.relatorios.listar_relatorios_chamadas", return_value=[]):
        from services.relatorios import listar_relatorios
        assert listar_relatorios(frequencia_baixa=True) == []


def test_chamada_sem_alunos_conta_como_zero_por_cento():
    """total_slots=0 vira percentual 0 em resumo_presenca, então é baixa frequência."""
    linhas = [_linha_chamada("c1", 0, 1, 0)]
    with patch("services.relatorios.listar_relatorios_chamadas", return_value=linhas):
        from services.relatorios import listar_relatorios
        assert [i["chamada_id"] for i in listar_relatorios(frequencia_baixa=True)] == ["c1"]


def test_rota_admin_repassa_os_filtros_novos():
    from routers.relatorios import listar_relatorios_admin
    with patch("routers.relatorios.listar_relatorios", return_value=[]) as m:
        listar_relatorios_admin(
            turma_id="t1",
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 5, 31),
            professor_id="p1",
            frequencia_baixa=True,
            current_user={"sub": "adm", "role": "Admin"},
        )
    kwargs = m.call_args.kwargs
    assert kwargs["data_inicio"] == date(2026, 5, 1)
    assert kwargs["data_fim"] == date(2026, 5, 31)
    assert kwargs["professor_id"] == "p1"
    assert kwargs["frequencia_baixa"] is True
    assert kwargs["turma_id"] == "t1"


def test_rota_admin_sem_filtros_nao_recorta():
    from routers.relatorios import listar_relatorios_admin
    with patch("routers.relatorios.listar_relatorios", return_value=[]) as m:
        listar_relatorios_admin(current_user={"sub": "adm", "role": "Admin"})
    kwargs = m.call_args.kwargs
    assert kwargs["data_inicio"] is None and kwargs["data_fim"] is None
    assert kwargs["professor_id"] is None
    assert kwargs["frequencia_baixa"] is False


def test_rota_admin_recusa_intervalo_invertido():
    from routers.relatorios import listar_relatorios_admin
    with pytest.raises(HTTPException) as exc:
        listar_relatorios_admin(
            data_inicio=date(2026, 5, 31),
            data_fim=date(2026, 5, 1),
            current_user={"sub": "adm", "role": "Admin"},
        )
    assert exc.value.status_code == 400
    assert "Intervalo de datas inválido" in exc.value.detail


def test_rota_admin_aceita_intervalo_de_um_dia_so():
    """inicio == fim é intervalo válido, não invertido."""
    from routers.relatorios import listar_relatorios_admin
    with patch("routers.relatorios.listar_relatorios", return_value=[]):
        out = listar_relatorios_admin(
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 5, 1),
            current_user={"sub": "adm", "role": "Admin"},
        )
    assert out == []


def test_rotulo_professor_usa_o_nome_da_primeira_linha():
    from routers.relatorios import _rotulo_professor_pdf

    assert _rotulo_professor_pdf("p1", [{"professor_nome": "Ana Souza"}]) == "Ana Souza"


def test_rotulo_professor_sem_filtro_e_none():
    from routers.relatorios import _rotulo_professor_pdf

    assert _rotulo_professor_pdf(None, [{"professor_nome": "Ana"}]) is None


def test_rotulo_professor_com_filtro_e_sem_resultado_nao_diz_todos():
    """None viraria 'todos' na linha de filtros — mentira num PDF recortado."""
    from routers.relatorios import _rotulo_professor_pdf

    assert _rotulo_professor_pdf("p1", []) == "filtro aplicado (sem chamadas no período)"
