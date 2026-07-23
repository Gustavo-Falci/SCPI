import time

import pytest

from core.limiter_storage import PostgresStorage

pytestmark = pytest.mark.usefixtures("pg")


def test_incr_conta_dentro_da_janela():
    s = PostgresStorage()
    assert s.incr("k1", 60) == 1
    assert s.incr("k1", 60) == 2
    assert s.get("k1") == 2


def test_get_chave_ausente_retorna_zero():
    s = PostgresStorage()
    assert s.get("nao-existe") == 0


def test_expiracao_reinicia_contador():
    s = PostgresStorage()
    assert s.incr("k2", 1) == 1
    time.sleep(1.2)
    assert s.get("k2") == 0
    assert s.incr("k2", 60) == 1


def test_get_expiry_no_futuro():
    s = PostgresStorage()
    s.incr("k3", 60)
    assert s.get_expiry("k3") > time.time()


def test_clear_remove_chave():
    s = PostgresStorage()
    s.incr("k4", 60)
    s.clear("k4")
    assert s.get("k4") == 0


def test_purgar_remove_expirados():
    from core.limiter_storage import purgar_rate_limit_buckets

    s = PostgresStorage()
    s.incr("k5", 1)
    time.sleep(1.2)
    assert purgar_rate_limit_buckets() >= 1
    assert s.get("k5") == 0
