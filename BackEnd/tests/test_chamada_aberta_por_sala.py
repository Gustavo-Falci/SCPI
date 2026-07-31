"""Resolução da chamada aberta a partir da sala (gate SCPI_RUN_DB_TESTS=1).

É por aqui que a câmera descobre em qual chamada gravar. Sala não é chave de
chamada: a mesma sala recebe turmas diferentes ao longo do dia, e basta um
professor esquecer a chamada aberta para existir mais de uma candidata. Sem
ordenação, o Postgres devolvia qualquer uma — e sincronizar na chamada errada
faz todo aluno presente levar 403 `nao_matriculado`, que a câmera trata como
definitivo: a turma inteira fica ausente, em silêncio, pela aula toda.
"""
import logging

import pytest

from infra.database import get_db_cursor


def _dia_semana_de_hoje():
    """Pergunta o dia ao próprio banco, na mesma convenção da query real.

    Usar o `weekday()` do Python arriscaria divergir do CURRENT_DATE do
    servidor (fuso/virada de dia) e deixaria o teste intermitente. ISODOW-1
    (segunda=0 … domingo=6) é idêntico ao `(DOW + 6) % 7` da query, e sem `%`
    no SQL — que, em execute() sem parâmetros, o psycopg2 não desescapa.
    """
    with get_db_cursor() as cur:
        cur.execute("SELECT EXTRACT(ISODOW FROM CURRENT_DATE)::int - 1 AS dia")
        return cur.fetchone()["dia"]


def _cadastrar_horario(turma_id, sala, dia_semana, hora_inicio, hora_fim):
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO horarios_aulas (turma_id, dia_semana, horario_inicio, "
            "horario_fim, sala) VALUES (%s, %s, %s, %s, %s)",
            (turma_id, dia_semana, hora_inicio, hora_fim, sala),
        )


def _abrir_chamada(turma_id, horas_atras=0):
    """Abre chamada com data_criacao no passado, simulando a aula anterior."""
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO Chamadas (turma_id, professor_id, data_chamada, "
            "horario_inicio, total_aulas, status, data_criacao) "
            "VALUES (%s, NULL, CURRENT_DATE, CURRENT_TIME, 1, 'Aberta', "
            "CURRENT_TIMESTAMP - make_interval(hours => %s)) "
            "RETURNING chamada_id",
            (turma_id, horas_atras),
        )
        return cur.fetchone()["chamada_id"]


@pytest.fixture
def academico_com_horarios(pg_academico):
    """pg_academico + limpeza de horarios_aulas.

    A FK horarios_aulas → Turmas não tem ON DELETE CASCADE, então sobra de
    horário aqui faz o teardown do pg_academico (DELETE FROM Turmas) explodir.
    """
    yield pg_academico

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM horarios_aulas WHERE turma_id = ANY(%s::uuid[])",
            ([pg_academico["turma3"], pg_academico["turma5"]],),
        )


def test_duas_chamadas_abertas_na_sala_devolve_a_mais_recente(
    academico_com_horarios, caplog
):
    """O cenário real: a chamada da manhã ficou aberta e a aula da tarde começa.

    A chamada antiga é inserida por ÚLTIMO de propósito: sem ORDER BY, a ordem
    física do heap tenderia a devolvê-la, que é justamente o erro.
    """
    from repositories.chamadas import obter_chamada_aberta_por_sala

    ids = academico_com_horarios
    sala = f"SALA-{ids['marca']}"
    dia = _dia_semana_de_hoje()

    _cadastrar_horario(ids["turma3"], sala, dia, "07:00", "08:40")
    _cadastrar_horario(ids["turma5"], sala, dia, "13:00", "14:40")

    chamada_tarde = _abrir_chamada(ids["turma5"], horas_atras=0)
    chamada_manha = _abrir_chamada(ids["turma3"], horas_atras=6)

    with caplog.at_level(logging.WARNING, logger="infra.database"):
        resultado = obter_chamada_aberta_por_sala(sala)

    assert resultado["chamada_id"] == chamada_tarde
    assert resultado["chamada_id"] != chamada_manha
    # O warning é o que transforma "a turma toda faltou" em algo depurável.
    assert any(sala in registro.getMessage() for registro in caplog.records)


def test_chamada_unica_na_sala_nao_gera_ambiguidade(academico_com_horarios, caplog):
    """Caso normal (ninguém esqueceu chamada aberta): devolve e não alerta."""
    from repositories.chamadas import obter_chamada_aberta_por_sala

    ids = academico_com_horarios
    sala = f"SALA-{ids['marca']}"
    dia = _dia_semana_de_hoje()

    _cadastrar_horario(ids["turma3"], sala, dia, "07:00", "08:40")
    chamada = _abrir_chamada(ids["turma3"])

    with caplog.at_level(logging.WARNING, logger="infra.database"):
        resultado = obter_chamada_aberta_por_sala(sala)

    assert resultado["chamada_id"] == chamada
    assert caplog.records == []


def test_sala_sem_chamada_aberta_devolve_none(academico_com_horarios):
    """Sem chamada aberta a câmera não deve sincronizar em nada."""
    from repositories.chamadas import obter_chamada_aberta_por_sala

    ids = academico_com_horarios
    sala = f"SALA-{ids['marca']}"
    _cadastrar_horario(ids["turma3"], sala, _dia_semana_de_hoje(), "07:00", "08:40")

    assert obter_chamada_aberta_por_sala(sala) is None
