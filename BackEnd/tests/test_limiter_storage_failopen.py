from contextlib import contextmanager
from unittest.mock import patch

from core.limiter_storage import PostgresStorage


@contextmanager
def _cursor_none(commit=False):
    yield None


def test_incr_fail_open_sem_conexao_libera():
    s = PostgresStorage()
    with patch("core.limiter_storage.get_db_cursor", _cursor_none):
        # sem DB: incr trata como início de janela (retorna amount), não levanta
        assert s.incr("x", 60) == 1
        assert s.get("x") == 0
        assert s.get_expiry("x")  # retorna epoch atual, sem exceção
