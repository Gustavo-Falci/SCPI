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


@pytest.fixture
def pg_academico(pg):
    """Semeia um cenário acadêmico mínimo e limpa depois.

    Cria 4 alunos cobrindo os casos que os filtros precisam distinguir:
    matriculado no semestre 3, matriculado no semestre 5, sem turma nenhuma e
    sem turno definido. Devolve os ids para os testes referenciarem.

    Sufixo aleatório em código de turma, RA e e-mail porque as três colunas são
    UNIQUE: sem isso a fixture colide com dados que já estejam no banco de teste.
    """
    import uuid

    from infra.migrations import _apply_all

    # Pipeline inteiro, não etapas escolhidas a dedo: colunas como
    # Colecao_Rostos.revogado_em nascem em migrations posteriores ao schema base,
    # e um schema pela metade quebra as queries que a aplicação realmente usa.
    _apply_all()

    marca = uuid.uuid4().hex[:8]
    ids = {
        "turma3": str(uuid.uuid4()), "turma5": str(uuid.uuid4()),
        "mat_s3": str(uuid.uuid4()), "mat_s5": str(uuid.uuid4()),
        "sem_turma": str(uuid.uuid4()), "sem_turno": str(uuid.uuid4()),
        "marca": marca,
    }
    alunos = ["mat_s3", "mat_s5", "sem_turma", "sem_turno"]

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO Turmas (turma_id, codigo_turma, nome_disciplina, "
            "periodo_letivo, turno, semestre) VALUES "
            "(%s, %s, 'Cálculo I', '2026/1', 'Matutino', '3'), "
            "(%s, %s, 'Cálculo II', '2026/2', 'Matutino', '5')",
            (ids["turma3"], f"MAT-101-{marca}", ids["turma5"], f"MAT-201-{marca}"),
        )
        for chave, nome, turno in [
            ("mat_s3", "Ana Souza", "Matutino"),
            ("mat_s5", "Bruno Lima", "Matutino"),
            ("sem_turma", "Carla Dias", "Matutino"),
            ("sem_turno", "Diego Reis", None),
        ]:
            usuario_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario) "
                "VALUES (%s, %s, %s, 'x', 'Aluno')",
                (usuario_id, nome, f"{chave}-{marca}@teste.local"),
            )
            cur.execute(
                "INSERT INTO Alunos (aluno_id, usuario_id, ra, turno) VALUES (%s, %s, %s, %s)",
                (ids[chave], usuario_id, f"RA-{chave}-{marca}", turno),
            )
        cur.execute(
            "INSERT INTO Turma_Alunos (turma_id, aluno_id) VALUES (%s, %s), (%s, %s)",
            (ids["turma3"], ids["mat_s3"], ids["turma5"], ids["mat_s5"]),
        )

    yield ids

    # Usuarios é a raiz: Alunos e Turma_Alunos caem por ON DELETE CASCADE.
    # O cast ::uuid[] é obrigatório: psycopg2 manda a lista Python como text[] e
    # o Postgres não tem operador uuid = text.
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM Usuarios WHERE usuario_id IN "
            "(SELECT usuario_id FROM Alunos WHERE aluno_id = ANY(%s::uuid[]))",
            ([ids[chave] for chave in alunos],),
        )
        cur.execute("DELETE FROM Turmas WHERE turma_id = ANY(%s::uuid[])",
                    ([ids["turma3"], ids["turma5"]],))
