import os
from datetime import datetime, timedelta

import pytest

from infra.database import get_db_cursor
from infra.migrations import ensure_reset_codes_table
from repositories.tokens import registrar_tentativa_codigo_invalida


def _db_ok():
    # Mesmo gate de segurança do conftest: só conecta com opt-in explícito.
    if os.getenv("SCPI_RUN_DB_TESTS") != "1":
        return False
    try:
        with get_db_cursor() as cur:
            if not cur:
                return False
            cur.execute("SELECT 1")
            cur.fetchone()
            return True
    except Exception:
        return False


@pytest.fixture
def reset_codes():
    if not _db_ok():
        pytest.skip("Postgres de teste indisponível (SCPI_RUN_DB_TESTS != 1).")
    ensure_reset_codes_table()
    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM PasswordResetCodes WHERE email=%s", ("z@x.com",))
        cur.execute(
            "INSERT INTO PasswordResetCodes (email, code, expires_at, used) "
            "VALUES (%s, %s, %s, FALSE)",
            ("z@x.com", "hash-fake", datetime.utcnow() + timedelta(minutes=15)),
        )
    yield
    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM PasswordResetCodes WHERE email=%s", ("z@x.com",))


def test_codigo_invalida_apos_5_tentativas(reset_codes):
    bloqueado = False
    for _ in range(5):
        _, bloqueado = registrar_tentativa_codigo_invalida("z@x.com", 5)
    assert bloqueado is True


def test_apos_invalidado_nao_reincrementa(reset_codes):
    for _ in range(5):
        registrar_tentativa_codigo_invalida("z@x.com", 5)
    # código já used=TRUE: não há row ativa -> (0, False), sem re-bloqueio
    tentativas, bloqueado = registrar_tentativa_codigo_invalida("z@x.com", 5)
    assert (tentativas, bloqueado) == (0, False)
