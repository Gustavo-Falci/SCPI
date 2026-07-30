"""Testes do repositório de consentimentos (sem DB real)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from repositories import consentimentos


def _mock_cursor(fetchone=None, fetchall=None):
    cur = MagicMock()
    cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall or []

    @contextmanager
    def fake_cursor(commit=False):
        yield cur

    return cur, fake_cursor


def test_registrar_evento_insere_com_todos_os_campos():
    cur, fake = _mock_cursor()
    with patch("repositories.consentimentos.get_db_cursor", fake):
        ok = consentimentos.registrar_evento(
            "aluno-1", "aceite", "1.0", ip="203.0.113.7",
            user_agent="Expo/1.0", origem="app",
        )
    assert ok is True
    sql, params = cur.execute.call_args[0]
    assert "INSERT INTO ConsentimentosLGPD" in sql
    assert params == ("aluno-1", "aceite", "1.0", "203.0.113.7", "Expo/1.0", "app")


def test_registrar_evento_trunca_user_agent_em_300():
    cur, fake = _mock_cursor()
    with patch("repositories.consentimentos.get_db_cursor", fake):
        consentimentos.registrar_evento("aluno-1", "aceite", "1.0",
                                        user_agent="x" * 500)
    params = cur.execute.call_args[0][1]
    assert len(params[4]) == 300


def test_registrar_evento_user_agent_vazio_vira_none():
    cur, fake = _mock_cursor()
    with patch("repositories.consentimentos.get_db_cursor", fake):
        consentimentos.registrar_evento("aluno-1", "aceite", "1.0", user_agent="")
    assert cur.execute.call_args[0][1][4] is None


def test_registrar_evento_sem_cursor_retorna_false():
    @contextmanager
    def sem_cursor(commit=False):
        yield None

    with patch("repositories.consentimentos.get_db_cursor", sem_cursor):
        assert consentimentos.registrar_evento("a", "aceite", "1.0") is False


def test_obter_ultimo_evento_desempata_por_id():
    # Backfill e aceite podem cair no mesmo timestamp; sem o tiebreak por
    # consentimento_id o "último" evento fica indefinido.
    cur, fake = _mock_cursor(fetchone={"evento": "aceite", "politica_versao": "1.0",
                                       "registrado_em": "2026-03-12T14:22:01"})
    with patch("repositories.consentimentos.get_db_cursor", fake):
        row = consentimentos.obter_ultimo_evento("aluno-1")
    sql = cur.execute.call_args[0][0]
    assert "ORDER BY registrado_em DESC, consentimento_id DESC" in sql
    assert "LIMIT 1" in sql
    assert row["evento"] == "aceite"


def test_obter_ultimo_evento_sem_registro_retorna_none():
    _, fake = _mock_cursor(fetchone=None)
    with patch("repositories.consentimentos.get_db_cursor", fake):
        assert consentimentos.obter_ultimo_evento("aluno-1") is None


def test_listar_trilha_ordem_cronologica_crescente():
    cur, fake = _mock_cursor(fetchall=[{"evento": "aceite"}, {"evento": "revogacao"}])
    with patch("repositories.consentimentos.get_db_cursor", fake):
        trilha = consentimentos.listar_trilha("aluno-1")
    sql = cur.execute.call_args[0][0]
    assert "ORDER BY registrado_em ASC, consentimento_id ASC" in sql
    assert len(trilha) == 2
