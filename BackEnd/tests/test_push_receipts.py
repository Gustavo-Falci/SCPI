"""Testes de receipts assíncronos: migração, repo, infra, job — sem DB/rede real."""
import inspect
import io
import json
from unittest.mock import MagicMock, patch


def _mock_cursor():
    cur = MagicMock()
    cur.rowcount = 0
    cur.fetchall.return_value = []
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return cm, cur


def test_ensure_push_receipts_table_cria_tabela():
    cm, cur = _mock_cursor()
    with patch("infra.migrations.get_db_cursor", return_value=cm):
        from infra.migrations import ensure_push_receipts_table
        ensure_push_receipts_table()
    sql = cur.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS PushReceiptsPendentes" in sql


def test_apply_all_registra_receipts():
    import infra.migrations as m
    assert "ensure_push_receipts_table()" in inspect.getsource(m._apply_all)


def test_registrar_tickets_pendentes_insere_com_on_conflict():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm), \
         patch("repositories.notificacoes.execute_values") as ev:
        from repositories.notificacoes import registrar_tickets_pendentes
        registrar_tickets_pendentes([{"id": "tk1", "token": "ExponentPushToken[a]"}])
    sql = ev.call_args[0][1]
    valores = ev.call_args[0][2]
    assert "INSERT INTO PushReceiptsPendentes" in sql
    assert "ON CONFLICT (ticket_id) DO NOTHING" in sql
    assert valores == [("tk1", "ExponentPushToken[a]")]
    assert "%" not in sql.replace("%s", "").replace("%%", "")


def test_registrar_tickets_pendentes_vazio_nao_insere():
    with patch("repositories.notificacoes.execute_values") as ev:
        from repositories.notificacoes import registrar_tickets_pendentes
        registrar_tickets_pendentes([])
    ev.assert_not_called()


def test_listar_tickets_pendentes_filtra_idade_e_limita():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm):
        from repositories.notificacoes import listar_tickets_pendentes
        listar_tickets_pendentes(900, 1000)
    sql, params = cur.execute.call_args[0]
    assert "FROM PushReceiptsPendentes" in sql
    assert "created_at <=" in sql
    assert "LIMIT %s" in sql
    assert params == (900, 1000)
    assert "%" not in sql.replace("%s", "").replace("%%", "")


def test_remover_tickets_pendentes_usa_any():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm):
        from repositories.notificacoes import remover_tickets_pendentes
        remover_tickets_pendentes(["tk1", "tk2"])
    sql, params = cur.execute.call_args[0]
    assert "DELETE FROM PushReceiptsPendentes" in sql
    assert "ticket_id = ANY(%s)" in sql
    assert params == (["tk1", "tk2"],)


def test_remover_tickets_pendentes_vazio_nao_executa():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm):
        from repositories.notificacoes import remover_tickets_pendentes
        remover_tickets_pendentes([])
    cur.execute.assert_not_called()


def test_remover_tickets_pendentes_antigos_por_idade():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm):
        from repositories.notificacoes import remover_tickets_pendentes_antigos
        remover_tickets_pendentes_antigos(86400)
    sql, params = cur.execute.call_args[0]
    assert "DELETE FROM PushReceiptsPendentes" in sql
    assert "created_at <=" in sql
    assert params == (86400,)
    assert "%" not in sql.replace("%s", "").replace("%%", "")
