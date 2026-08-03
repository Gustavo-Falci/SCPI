"""Colunas de data das tabelas de token viram TIMESTAMPTZ, com o valor certo.

Gate SCPI_RUN_DB_TESTS=1 (service postgres:16 do CI). Não dá para testar isto
com cursor mockado: o que importa é o que o Postgres faz com o `USING ... AT
TIME ZONE`, e um mock não converte nada.

O caso que justifica o teste é o da sessão em fuso != UTC. Ali `expires_at`
(gravado em UTC pelo Python) e `created_at` (gravado pelo `NOW()` do banco, em
hora de parede local) precisam de conversões DIFERENTES. Uma cláusula única
para as duas deslocaria uma delas pelo offset — silenciosamente, e só em
produção, onde o fuso não é UTC.
"""
import pytest

from tests.conftest import _db_disponivel

pytestmark = pytest.mark.skipif(
    not _db_disponivel(), reason="requer SCPI_RUN_DB_TESTS=1 e Postgres acessível"
)

COLUNAS = {
    "refreshtokens": {"expires_at", "created_at", "revoked_at"},
    "passwordresetcodes": {"expires_at", "created_at", "token_consumido_em"},
}


def _tipos(cur, tabela):
    cur.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = %s",
        (tabela,),
    )
    return {r["column_name"]: r["data_type"] for r in cur.fetchall()}


@pytest.mark.parametrize("tabela", sorted(COLUNAS))
def test_colunas_sao_timestamptz_e_migration_e_idempotente(tabela):
    from infra.database import get_db_cursor
    from infra.migrations import _apply_all, ensure_timestamptz_tokens

    _apply_all()
    ensure_timestamptz_tokens()  # segunda passada não pode quebrar nem reescrever

    with get_db_cursor() as cur:
        tipos = _tipos(cur, tabela)

    for coluna in COLUNAS[tabela]:
        assert tipos.get(coluna) == "timestamp with time zone", (
            f"{tabela}.{coluna} ficou como {tipos.get(coluna)!r}"
        )


@pytest.mark.parametrize("fuso", ["UTC", "America/Sao_Paulo", "Asia/Tokyo"])
def test_valor_gravado_sobrevive_a_conversao_em_qualquer_fuso(fuso):
    """Simula a tabela ANTIGA e confere que a conversão não desloca a hora.

    Parametrizado por fuso porque com TimeZone=UTC — que é como o Postgres do
    CI sobe — as duas cláusulas `AT TIME ZONE` dão no mesmo e o teste não
    provaria nada. Só em fuso deslocado é que uma cláusula única para os dois
    grupos erraria, e é essa a situação possível em produção.

    `SET LOCAL` e não `SET`: a conexão vem de pool, e um TimeZone vazado ficaria
    grudado nela para o próximo que a pegasse.
    """
    from datetime import timedelta

    from core.tempo import agora_utc
    from infra.database import get_db_cursor

    with get_db_cursor(commit=True) as cur:
        cur.execute(f"SET LOCAL TimeZone TO '{fuso}'")
        cur.execute("DROP TABLE IF EXISTS _tz_probe")
        cur.execute(
            "CREATE TABLE _tz_probe ("
            "  expires_at TIMESTAMP NOT NULL,"  # gravado pelo Python, em UTC
            "  created_at TIMESTAMP NOT NULL"   # gravado pelo banco, hora local
            ")"
        )
        # O Python grava UTC; para caber na coluna naive, tira o tzinfo — é
        # exatamente o que o código fazia antes desta branch.
        momento = agora_utc()
        cur.execute(
            "INSERT INTO _tz_probe (expires_at, created_at) VALUES (%s, NOW())",
            (momento.replace(tzinfo=None),),
        )
        cur.execute(
            "ALTER TABLE _tz_probe ALTER COLUMN expires_at "
            "TYPE timestamptz USING expires_at AT TIME ZONE 'UTC'"
        )
        cur.execute(
            "ALTER TABLE _tz_probe ALTER COLUMN created_at "
            "TYPE timestamptz USING created_at AT TIME ZONE current_setting('TimeZone')"
        )
        cur.execute("SELECT expires_at, created_at FROM _tz_probe")
        linha = cur.fetchone()
        cur.execute("DROP TABLE _tz_probe")

    assert abs(linha["expires_at"] - momento) < timedelta(seconds=5), (
        f"expires_at deslocou em TimeZone={fuso}"
    )
    # O ponto do teste: depois da conversão os dois marcam o MESMO instante,
    # independentemente do TimeZone da sessão.
    assert abs(linha["expires_at"] - linha["created_at"]) < timedelta(seconds=5), (
        f"expires_at e created_at divergiram em TimeZone={fuso}"
    )


def test_ciclo_do_refresh_token_com_datetime_aware():
    """Grava e lê de volta pelo caminho real do repositório."""
    from core.auth_utils import create_refresh_token
    from infra.database import get_db_cursor
    from infra.migrations import _apply_all
    from repositories.tokens import inserir_refresh_token, rotacionar_refresh_token

    _apply_all()
    plain, token_hash, expires_at = create_refresh_token()
    assert expires_at.tzinfo is not None, "create_refresh_token deveria devolver aware"

    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM RefreshTokens WHERE usuario_id = %s", ("tz-probe",))

    assert inserir_refresh_token(token_hash, "tz-probe", expires_at) is True

    _, hash_novo, expires_novo = create_refresh_token()
    resultado = rotacionar_refresh_token(token_hash, hash_novo, expires_novo)
    # Não pode ser "expired": a comparação naive-vs-aware levantaria TypeError,
    # e um token de dias no futuro nunca deveria expirar aqui.
    assert resultado.get("_status") != "expired"
    assert resultado["usuario_id"] == "tz-probe" or resultado.get("_status") == "invalid"

    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM RefreshTokens WHERE usuario_id = %s", ("tz-probe",))
