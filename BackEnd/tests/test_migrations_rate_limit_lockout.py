from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from infra.migrations import ensure_rate_limit_table, ensure_login_attempts_table


def _run(func):
    executed = []
    cur = MagicMock()
    cur.execute.side_effect = lambda *a, **k: executed.append(a[0])

    @contextmanager
    def fake_cursor(commit=False):
        yield cur

    with patch("infra.migrations.get_db_cursor", fake_cursor):
        func()
    return " ".join(executed)


def test_ensure_rate_limit_table_cria_tabela_e_indice():
    sql = _run(ensure_rate_limit_table)
    assert "CREATE TABLE IF NOT EXISTS rate_limit_buckets" in sql
    assert "ix_rate_limit_buckets_expires" in sql


def test_ensure_login_attempts_table_cria_tabela():
    sql = _run(ensure_login_attempts_table)
    assert "CREATE TABLE IF NOT EXISTS login_attempts" in sql
    assert "email" in sql and "locked_until" in sql
