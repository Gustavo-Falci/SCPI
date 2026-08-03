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


@pytest.fixture
def usuario_probe():
    """Usuário real, porque `rotacionar_refresh_token` faz JOIN com Usuarios.

    Sem a linha em Usuarios o JOIN não casa, a função devolve `invalid` e
    retorna ANTES de comparar `expires_at` — o teste passaria sem nunca ter
    exercitado a comparação aware que é o motivo dele existir.
    """
    import uuid

    from infra.database import get_db_cursor
    from infra.migrations import _apply_all

    _apply_all()
    usuario_id = str(uuid.uuid4())
    marca = usuario_id[:8]
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario) "
            "VALUES (%s, 'TZ Probe', %s, 'x', 'Aluno')",
            (usuario_id, f"tz-probe-{marca}@teste.local"),
        )

    yield usuario_id

    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM RefreshTokens WHERE usuario_id = %s", (usuario_id,))
        cur.execute("DELETE FROM Usuarios WHERE usuario_id = %s::uuid", (usuario_id,))


def test_ciclo_do_refresh_token_com_datetime_aware(usuario_probe):
    """Grava e lê de volta pelo caminho real do repositório.

    O `_status == "ok"` é o que prova o ponto: para chegar nele a função
    passou pela comparação `row["expires_at"] < agora_utc()`, que levantaria
    TypeError se a coluna tivesse ficado naive.
    """
    from core.auth_utils import create_refresh_token
    from repositories.tokens import inserir_refresh_token, rotacionar_refresh_token

    _, token_hash, expires_at = create_refresh_token()
    assert expires_at.tzinfo is not None, "create_refresh_token deveria devolver aware"

    assert inserir_refresh_token(token_hash, usuario_probe, expires_at) is True

    _, hash_novo, expires_novo = create_refresh_token()
    resultado = rotacionar_refresh_token(token_hash, hash_novo, expires_novo)

    assert resultado["_status"] == "ok", f"rotação falhou: {resultado}"
    assert resultado["row"]["usuario_id"] == usuario_probe
    assert resultado["row"]["expires_at"].tzinfo is not None, (
        "psycopg2 devolveu expires_at naive — a coluna não é TIMESTAMPTZ"
    )
