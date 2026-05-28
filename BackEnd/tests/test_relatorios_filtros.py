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


def test_listar_opcoes_filtros_relatorios_deriva_distintos():
    rows = [
        {"turma_id": "T1", "nome_disciplina": "Calculo", "codigo_turma": "C1",
         "turno": "Matutino", "semestre": "2026.1"},
        {"turma_id": "T2", "nome_disciplina": "Fisica", "codigo_turma": "C2",
         "turno": "Noturno", "semestre": "2025.2"},
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
