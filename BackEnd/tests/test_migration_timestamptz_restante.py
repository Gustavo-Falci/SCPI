"""As demais colunas de data viram TIMESTAMPTZ preservando o instante.

Gate SCPI_RUN_DB_TESTS=1. Complementa test_migration_timestamptz_tokens.py.

Diferença em relação às tabelas de token: aqui a semântica NÃO estava mista.
Todas estas colunas são escritas só por `NOW()`/`CURRENT_TIMESTAMP`, logo todas
guardam hora de parede da sessão e todas usam a MESMA cláusula de conversão.
Usar `AT TIME ZONE 'UTC'` (como nas de token) deslocaria tudo pelo offset — é
justamente isso que o teste parametrizado por fuso pega.
"""
import pytest

from tests.conftest import _db_disponivel

pytestmark = pytest.mark.skipif(
    not _db_disponivel(), reason="requer SCPI_RUN_DB_TESTS=1 e Postgres acessível"
)

COLUNAS = [
    ("usuarios", "data_cadastro"),
    ("turma_alunos", "data_associacao"),
    ("chamadas", "data_criacao"),
    ("presencas", "hora_registro"),
    ("colecao_rostos", "data_indexacao"),
    ("colecao_rostos", "consentimento_data"),
    ("colecao_rostos", "revogado_em"),
    ("consentimentoslgpd", "registrado_em"),
    ("pushtokens", "updated_at"),
    ("pushreceiptspendentes", "created_at"),
]


@pytest.mark.parametrize("tabela,coluna", COLUNAS, ids=lambda v: str(v))
def test_coluna_e_timestamptz(tabela, coluna):
    from infra.database import get_db_cursor
    from infra.migrations import _apply_all, ensure_timestamptz_restante

    _apply_all()
    ensure_timestamptz_restante()  # segunda passada não pode quebrar nem reescrever

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s",
            (tabela, coluna),
        )
        row = cur.fetchone()

    assert row, f"{tabela}.{coluna} não existe"
    assert row["data_type"] == "timestamp with time zone", (
        f"{tabela}.{coluna} ficou como {row['data_type']!r}"
    )


@pytest.mark.parametrize("fuso", ["UTC", "America/Sao_Paulo", "Asia/Tokyo"])
def test_conversao_preserva_o_instante_gravado_por_now(fuso):
    """A hora de parede gravada por NOW() tem de continuar apontando o mesmo instante.

    Parametrizado por fuso porque com TimeZone=UTC — como o Postgres do CI sobe
    — a cláusula certa e a errada coincidem, e o teste não provaria nada.

    `SET LOCAL`: a conexão vem de pool e um TimeZone vazado ficaria grudado nela.
    """
    from datetime import timedelta

    from infra.database import get_db_cursor

    with get_db_cursor(commit=True) as cur:
        cur.execute(f"SET LOCAL TimeZone TO '{fuso}'")
        cur.execute("DROP TABLE IF EXISTS _tz_probe_restante")
        cur.execute("CREATE TABLE _tz_probe_restante (marcado_em TIMESTAMP NOT NULL)")
        # Guarda o instante de referência ANTES da conversão, como timestamptz.
        cur.execute("INSERT INTO _tz_probe_restante (marcado_em) VALUES (NOW())")
        cur.execute("SELECT now() AS agora")
        referencia = cur.fetchone()["agora"]

        cur.execute(
            "ALTER TABLE _tz_probe_restante ALTER COLUMN marcado_em "
            "TYPE timestamptz USING marcado_em AT TIME ZONE current_setting('TimeZone')"
        )
        cur.execute("SELECT marcado_em FROM _tz_probe_restante")
        convertido = cur.fetchone()["marcado_em"]
        cur.execute("DROP TABLE _tz_probe_restante")

    assert abs(convertido - referencia) < timedelta(seconds=5), (
        f"instante deslocou em TimeZone={fuso}: {convertido} != {referencia}"
    )


def test_clausula_utc_deslocaria_o_valor_em_fuso_nao_utc():
    """Pina POR QUE a cláusula é current_setting e não 'UTC'.

    Se alguém "uniformizar" as duas migrações usando 'UTC' aqui, o valor anda
    pelo offset. Este teste demonstra o erro em vez de descrevê-lo em comentário.
    """
    from datetime import timedelta

    from infra.database import get_db_cursor

    with get_db_cursor(commit=True) as cur:
        cur.execute("SET LOCAL TimeZone TO 'America/Sao_Paulo'")
        cur.execute("DROP TABLE IF EXISTS _tz_probe_errado")
        cur.execute("CREATE TABLE _tz_probe_errado (marcado_em TIMESTAMP NOT NULL)")
        cur.execute("INSERT INTO _tz_probe_errado (marcado_em) VALUES (NOW())")
        cur.execute("SELECT now() AS agora")
        referencia = cur.fetchone()["agora"]

        cur.execute(
            "ALTER TABLE _tz_probe_errado ALTER COLUMN marcado_em "
            "TYPE timestamptz USING marcado_em AT TIME ZONE 'UTC'"
        )
        cur.execute("SELECT marcado_em FROM _tz_probe_errado")
        errado = cur.fetchone()["marcado_em"]
        cur.execute("DROP TABLE _tz_probe_errado")

    # -03:00 lido como UTC vira 3h no futuro.
    assert abs(errado - referencia) > timedelta(hours=2), (
        "a cláusula 'UTC' deveria ter deslocado o valor — se não deslocou, o "
        "banco de teste está em UTC e este teste perdeu o sentido"
    )
