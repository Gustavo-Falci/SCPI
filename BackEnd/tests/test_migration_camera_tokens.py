"""A tabela de tokens da câmera precisa existir de fato no banco."""
import pytest

from tests.conftest import _db_disponivel

pytestmark = pytest.mark.skipif(
    not _db_disponivel(), reason="requer SCPI_RUN_DB_TESTS=1 e Postgres acessível"
)


def test_tabela_existe_e_migration_e_idempotente():
    from infra.database import get_db_cursor
    from infra.migrations import ensure_camera_tokens_table

    ensure_camera_tokens_table()
    ensure_camera_tokens_table()

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'camera_tokens'"
        )
        colunas = {r["column_name"] for r in cur.fetchall()}

    assert {"id", "sala", "token_hash", "descricao", "criado_em", "ultimo_uso_em", "revogado_em"} <= colunas


def test_emitir_buscar_revogar():
    from repositories.camera_tokens import buscar_sala_por_token, emitir_token, revogar_token
    from infra.database import get_db_cursor
    from infra.migrations import ensure_camera_tokens_table

    ensure_camera_tokens_table()
    token = emitir_token("Sala de Teste 999", "teste automatizado")

    assert buscar_sala_por_token(token) == "Sala de Teste 999"

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT id FROM camera_tokens WHERE sala = %s ORDER BY id DESC LIMIT 1",
            ("Sala de Teste 999",),
        )
        token_id = cur.fetchone()["id"]

    assert revogar_token(token_id) is True
    assert buscar_sala_por_token(token) is None

    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM camera_tokens WHERE sala = %s", ("Sala de Teste 999",))
