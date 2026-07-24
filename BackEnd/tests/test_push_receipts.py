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
