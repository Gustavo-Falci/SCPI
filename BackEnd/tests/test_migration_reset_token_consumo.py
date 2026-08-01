"""A coluna de consumo do reset_token precisa existir de fato no banco."""
import pytest

from tests.conftest import _db_disponivel

pytestmark = pytest.mark.skipif(
    not _db_disponivel(), reason="requer SCPI_RUN_DB_TESTS=1 e Postgres acessível"
)


def test_coluna_token_consumido_em_existe_e_e_idempotente():
    from infra.database import get_db_cursor
    from infra.migrations import ensure_reset_token_consumo

    ensure_reset_token_consumo()
    ensure_reset_token_consumo()  # idempotência

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT data_type FROM information_schema.columns
             WHERE LOWER(table_name) = 'passwordresetcodes'
               AND column_name = 'token_consumido_em'
            """
        )
        assert cur.fetchone() is not None
