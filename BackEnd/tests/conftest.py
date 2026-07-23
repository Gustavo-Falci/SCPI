import os

import pytest

from infra.database import get_db_cursor


_db_cache = None


def _db_disponivel():
    """Só conecta quando SCPI_RUN_DB_TESTS=1 está setado (CI com Postgres service).

    Opt-in explícito por segurança: sem a flag, os testes de integração são
    pulados SEM tentar conectar — impede rodar TRUNCATE contra o DB real que o
    .env de dev aponta (DB_HOST de produção). Memoizado para não repetir o probe.
    """
    global _db_cache
    if _db_cache is not None:
        return _db_cache
    if os.getenv("SCPI_RUN_DB_TESTS") != "1":
        _db_cache = False
        return _db_cache
    try:
        with get_db_cursor() as cur:
            if not cur:
                _db_cache = False
            else:
                cur.execute("SELECT 1")
                cur.fetchone()
                _db_cache = True
    except Exception:
        _db_cache = False
    return _db_cache


@pytest.fixture(autouse=True, scope="session")
def _limiter_em_memoria():
    """Força o limiter global a usar storage em memória durante os testes.

    Sem isso, qualquer endpoint com @limiter.limit (ex.: /health) chamado via
    TestClient dispara PostgresStorage.incr → conexão ao DB_HOST do .env de dev
    (produção) a cada request, pendurando ~1 connect-timeout por chamada.
    Os testes de integração do storage instanciam PostgresStorage diretamente e
    não são afetados por este swap.
    """
    from limits.storage import MemoryStorage
    from limits.strategies import STRATEGIES

    from core.limiter import limiter

    limiter._storage = MemoryStorage()
    limiter._limiter = STRATEGIES["fixed-window"](limiter._storage)
    yield


@pytest.fixture
def pg():
    """Prepara o Postgres de teste: garante tabelas e limpa estado.

    Pula o teste se não houver banco (dev sem Postgres local; CI tem o service).
    """
    if not _db_disponivel():
        pytest.skip("Postgres de teste indisponível (DB_* não configurado).")

    from infra.migrations import ensure_rate_limit_table, ensure_login_attempts_table

    ensure_rate_limit_table()
    ensure_login_attempts_table()

    with get_db_cursor(commit=True) as cur:
        cur.execute("TRUNCATE rate_limit_buckets")
        cur.execute("TRUNCATE login_attempts")

    yield

    with get_db_cursor(commit=True) as cur:
        cur.execute("TRUNCATE rate_limit_buckets")
        cur.execute("TRUNCATE login_attempts")
