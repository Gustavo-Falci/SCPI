import logging

import infra.database as _db
from infra.database import get_db_cursor

logger = logging.getLogger("scpi.migrations")

# Chave fixa arbitrária para o advisory lock que serializa as migrações
# entre os múltiplos workers do gunicorn (evita race em CREATE TABLE/TYPE).
_MIGRATION_LOCK_KEY = 4815162342


def ensure_base_schema():
    """Cria as tabelas-base do domínio (idempotente).

    Antes ficavam só no schema_inicial.sql (aplicado manualmente uma vez).
    Aqui elas são recriadas no startup se ausentes — banco novo se auto-monta.
    Colunas/constraints adicionadas depois por migração ficam nas funções
    `ensure_*` específicas; aqui só o conjunto pré-migração (cada coluna tem
    um único dono).
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Usuarios (
                usuario_id uuid PRIMARY KEY,
                nome varchar(255) NOT NULL,
                email varchar(255) NOT NULL UNIQUE,
                senha varchar(255) NOT NULL,
                tipo_usuario varchar(50) NOT NULL,
                data_cadastro timestamptz DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Professores (
                professor_id uuid PRIMARY KEY,
                usuario_id uuid NOT NULL UNIQUE
                    REFERENCES Usuarios(usuario_id) ON DELETE CASCADE,
                data_admissao date
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Alunos (
                aluno_id uuid PRIMARY KEY,
                usuario_id uuid NOT NULL UNIQUE
                    REFERENCES Usuarios(usuario_id) ON DELETE CASCADE,
                ra varchar(100) NOT NULL UNIQUE,
                turno varchar(20)
                    CHECK (turno IN ('Matutino', 'Noturno'))
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Turmas (
                turma_id uuid PRIMARY KEY,
                professor_id uuid
                    REFERENCES Professores(professor_id) ON DELETE CASCADE,
                codigo_turma varchar(50) NOT NULL UNIQUE,
                nome_disciplina varchar(255) NOT NULL,
                periodo_letivo varchar(50),
                sala_padrao varchar(100),
                turno varchar(20),
                semestre varchar(20)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Turma_Alunos (
                turma_aluno_id serial PRIMARY KEY,
                turma_id uuid NOT NULL
                    REFERENCES Turmas(turma_id) ON DELETE CASCADE,
                aluno_id uuid NOT NULL
                    REFERENCES Alunos(aluno_id) ON DELETE CASCADE,
                data_associacao timestamptz DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (turma_id, aluno_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Horarios_Aulas (
                horario_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                turma_id uuid REFERENCES Turmas(turma_id),
                dia_semana integer,
                horario_inicio time,
                horario_fim time,
                sala text
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Chamadas (
                chamada_id serial PRIMARY KEY,
                turma_id uuid NOT NULL
                    REFERENCES Turmas(turma_id) ON DELETE CASCADE,
                professor_id uuid
                    REFERENCES Professores(professor_id) ON DELETE CASCADE,
                data_chamada date NOT NULL,
                horario_inicio time NOT NULL,
                horario_fim time,
                status varchar(50) DEFAULT 'Aberta',
                data_criacao timestamptz DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Presencas (
                presenca_id serial PRIMARY KEY,
                chamada_id integer NOT NULL
                    REFERENCES Chamadas(chamada_id) ON DELETE CASCADE,
                aluno_id uuid NOT NULL
                    REFERENCES Alunos(aluno_id) ON DELETE CASCADE,
                hora_registro timestamptz DEFAULT CURRENT_TIMESTAMP,
                tipo_registro varchar(50) DEFAULT 'Reconhecimento'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Colecao_Rostos (
                colecao_rosto_id serial PRIMARY KEY,
                aluno_id uuid NOT NULL
                    REFERENCES Alunos(aluno_id) ON DELETE CASCADE,
                external_image_id varchar(255) NOT NULL,
                face_id_rekognition varchar(255),
                s3_path_cadastro varchar(500),
                data_indexacao timestamptz DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def ensure_professor_departamento_dropped():
    """Remove a coluna departamento de Professores (idempotente).

    Campo cosmético sem uso em nenhuma regra de negócio. Produção não tinha
    dado preenchido, então o DROP não perde informação relevante.
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "ALTER TABLE Professores DROP COLUMN IF EXISTS departamento"
        )


def ensure_chamada_professor_nullable():
    """Torna chamadas.professor_id nullable (idempotente).

    A exclusão de professor orfana as chamadas (professor_id = NULL) para
    preservar o histórico de presença. Espelha turmas.professor_id, que já é
    nullable. Sem isso, excluir professor com chamada dá NotNullViolation.
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "ALTER TABLE Chamadas ALTER COLUMN professor_id DROP NOT NULL"
        )


def ensure_lgpd_columns():
    """Adiciona colunas de consentimento/revogação de biometria (idempotente)."""
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            ALTER TABLE Colecao_Rostos
            ADD COLUMN IF NOT EXISTS consentimento_biometrico BOOLEAN NOT NULL DEFAULT FALSE
            """
        )
        cur.execute(
            """
            ALTER TABLE Colecao_Rostos
            ADD COLUMN IF NOT EXISTS consentimento_data TIMESTAMPTZ NULL
            """
        )
        cur.execute(
            """
            ALTER TABLE Colecao_Rostos
            ADD COLUMN IF NOT EXISTS revogado_em TIMESTAMPTZ NULL
            """
        )


def ensure_consentimentos_table():
    """Trilha append-only de consentimento LGPD + backfill da base existente.

    Nunca sofre UPDATE/DELETE: revogar é inserir um evento novo. O backfill
    marca quem já tem biometria ativa como aceite 'legado' — honesto sobre a
    origem do dado, sem inventar prova de um aceite versionado que não houve.
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ConsentimentosLGPD (
                consentimento_id SERIAL PRIMARY KEY,
                aluno_id         UUID NOT NULL REFERENCES Alunos(aluno_id),
                evento           VARCHAR(20) NOT NULL,
                politica_versao  VARCHAR(20) NOT NULL,
                registrado_em    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ip               VARCHAR(45),
                user_agent       TEXT,
                origem           VARCHAR(20) NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_consent_aluno "
            "ON ConsentimentosLGPD (aluno_id, registrado_em DESC)"
        )
        # NOT EXISTS: os 4 workers gunicorn chamam run_all() no startup.
        cur.execute(
            """
            INSERT INTO ConsentimentosLGPD
                (aluno_id, evento, politica_versao, registrado_em, origem)
            SELECT cr.aluno_id, 'aceite', 'legado',
                   COALESCE(MIN(cr.consentimento_data), CURRENT_TIMESTAMP), 'backfill'
            FROM Colecao_Rostos cr
            WHERE cr.revogado_em IS NULL AND cr.consentimento_biometrico = TRUE
              AND NOT EXISTS (
                  SELECT 1 FROM ConsentimentosLGPD c WHERE c.aluno_id = cr.aluno_id
              )
            GROUP BY cr.aluno_id
            """
        )


def ensure_refresh_tokens_table():
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS RefreshTokens (
                token_hash VARCHAR(128) PRIMARY KEY,
                usuario_id VARCHAR(64) NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                revoked_at TIMESTAMPTZ NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_refresh_usuario ON RefreshTokens (usuario_id)"
        )


def ensure_push_tokens_table():
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS PushTokens (
                usuario_id VARCHAR(64) PRIMARY KEY,
                expo_token TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def ensure_push_receipts_table():
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS PushReceiptsPendentes (
                ticket_id  TEXT PRIMARY KEY,
                expo_token TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def ensure_primeiro_acesso_column():
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            ALTER TABLE Usuarios
            ADD COLUMN IF NOT EXISTS primeiro_acesso BOOLEAN NOT NULL DEFAULT FALSE
            """
        )


def ensure_reset_codes_table():
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS PasswordResetCodes (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                code VARCHAR(6) NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                used BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        # code agora guarda HMAC-SHA256 (64 hex), não mais o código em texto.
        cur.execute(
            "ALTER TABLE PasswordResetCodes ALTER COLUMN code TYPE VARCHAR(64)"
        )
        # Contador de tentativas para lockout por conta (anti brute-force).
        cur.execute(
            "ALTER TABLE PasswordResetCodes "
            "ADD COLUMN IF NOT EXISTS tentativas INT NOT NULL DEFAULT 0"
        )


def ensure_reset_token_consumo():
    """Coluna que torna o reset_token de uso único (A4). Idempotente.

    O código de 6 dígitos já era de uso único; o JWT que ele gera não era —
    valia por 15 minutos e servia para quantas trocas de senha o portador
    quisesse.
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "ALTER TABLE PasswordResetCodes "
            "ADD COLUMN IF NOT EXISTS token_consumido_em TIMESTAMPTZ"
        )


def ensure_rate_limit_table():
    """Tabela do rate-limit compartilhado entre workers (M4). Idempotente."""
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_limit_buckets (
                key         TEXT        PRIMARY KEY,
                count       INTEGER     NOT NULL,
                expires_at  TIMESTAMPTZ NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_rate_limit_buckets_expires "
            "ON rate_limit_buckets (expires_at)"
        )


def ensure_login_attempts_table():
    """Tabela de lockout de login por conta (B1). Idempotente."""
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS login_attempts (
                email         TEXT        PRIMARY KEY,
                fails         INTEGER     NOT NULL DEFAULT 0,
                first_fail_at TIMESTAMPTZ,
                locked_until  TIMESTAMPTZ
            )
            """
        )


def ensure_camera_tokens_table():
    """Tokens de serviço da câmera, um por sala (A6). Idempotente.

    Substitui o CAMERA_SERVICE_TOKEN global de env: com a sala no banco, um
    token vazado só serve para a sala dele, e a revogação é individual.
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS camera_tokens (
                id            SERIAL PRIMARY KEY,
                sala          TEXT NOT NULL,
                token_hash    TEXT NOT NULL UNIQUE,
                descricao     TEXT,
                criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ultimo_uso_em TIMESTAMPTZ,
                revogado_em   TIMESTAMPTZ
            )
            """
        )


def ensure_presenca_por_aula():
    """Adiciona total_aulas em chamadas e num_aula em presencas (idempotente)."""
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "ALTER TABLE chamadas ADD COLUMN IF NOT EXISTS total_aulas smallint NOT NULL DEFAULT 1"
        )
        cur.execute(
            "ALTER TABLE presencas ADD COLUMN IF NOT EXISTS num_aula smallint NOT NULL DEFAULT 1"
        )
        cur.execute(
            "ALTER TABLE presencas DROP CONSTRAINT IF EXISTS presencas_chamada_id_aluno_id_key"
        )
        cur.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    JOIN pg_namespace n ON t.relnamespace = n.oid
                    WHERE c.conname = 'presencas_chamada_aluno_aula_key'
                      AND n.nspname = current_schema()
                ) THEN
                    ALTER TABLE presencas
                      ADD CONSTRAINT presencas_chamada_aluno_aula_key
                        UNIQUE (chamada_id, aluno_id, num_aula);
                END IF;
            END$$;
            """
        )


def ensure_multi_angle_faces():
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            ALTER TABLE Colecao_Rostos
            ADD COLUMN IF NOT EXISTS angulo VARCHAR(50) NOT NULL DEFAULT 'frontal'
        """)
        cur.execute("""
            ALTER TABLE Colecao_Rostos
            DROP CONSTRAINT IF EXISTS colecao_rostos_external_image_id_key
        """)
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_colecao_rostos_aluno_angulo'
                ) THEN
                    ALTER TABLE Colecao_Rostos
                    ADD CONSTRAINT uq_colecao_rostos_aluno_angulo
                    UNIQUE (aluno_id, angulo);
                END IF;
            END $$;
        """)


def ensure_chamada_aberta_unica():
    """Garante no máximo uma chamada com status='Aberta' por turma (defesa contra race condition)."""
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_chamada_aberta_por_turma
            ON Chamadas (turma_id)
            WHERE status = 'Aberta'
            """
        )


def ensure_indices_filtros_alunos():
    """Índices que sustentam os filtros da aba Alunos do portal.

    listar_alunos_para_admin bate em Turma_Alunos por aluno_id (EXISTS de escopo
    e COUNT de turmas) e recorta Turmas por semestre. Sem eles, cada página da
    lista vira seq scan — o que dói justamente no cliente grande que motivou os
    filtros.
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_turma_alunos_aluno "
            "ON Turma_Alunos (aluno_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_turmas_semestre "
            "ON Turmas (semestre)"
        )


def ensure_indices_performance():
    """Índices do caminho quente da câmera e dos relatórios.

    O primeiro é o que dói: obter_chamada_aberta_por_sala roda a cada burst da
    câmera (poucos segundos, por sala, aula inteira) e filtra horarios_aulas por
    sala + dia_semana — sem índice é seq scan da tabela toda a cada rosto
    reconhecido. Os demais cobrem os JOINs por turma_id e os recortes das telas
    de relatório (por professor, por data), que hoje varrem Chamadas inteira.

    Presencas (aluno_id) não é redundante com a unique (chamada_id, aluno_id,
    num_aula): aquela só serve consulta que começa por chamada_id; o histórico
    do aluno começa por aluno_id.
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_horarios_sala_dia "
            "ON Horarios_Aulas (sala, dia_semana)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_horarios_turma "
            "ON Horarios_Aulas (turma_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_presencas_aluno "
            "ON Presencas (aluno_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chamadas_turma_status "
            "ON Chamadas (turma_id, status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chamadas_professor "
            "ON Chamadas (professor_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chamadas_data "
            "ON Chamadas (data_chamada)"
        )


# Nomes, não referências: os testes de pipeline usam patch.object(m, nome, stub)
# e uma lista de referências capturaria as funções originais no import, fazendo
# o patch virar no-op silencioso.
def ensure_timestamptz_tokens():
    """Converte as colunas de data das tabelas de token para TIMESTAMPTZ.

    Motivo: `RefreshTokens` e `PasswordResetCodes` tinham semântica MISTA. As
    colunas `expires_at` recebiam UTC vindo do Python, enquanto `created_at`,
    `revoked_at` e `token_consumido_em` recebiam `NOW()`/`CURRENT_TIMESTAMP`,
    que num `timestamp` sem tz grava a hora de PAREDE da sessão. Se o TimeZone
    do banco não for UTC, os dois grupos estavam deslocados entre si — e
    `purgar_tokens_expirados` ("expires_at < NOW()") comparava um contra o
    outro, apagando refresh token cedo ou tarde demais pelo offset.

    Por isso a conversão usa cláusulas DIFERENTES por grupo:
      - `expires_at`      → interpretar o valor gravado como UTC
      - as demais         → interpretar como o TimeZone da sessão

    Com TimeZone = UTC as duas são idênticas, então o DDL está correto nos dois
    cenários e não depende de descobrir a configuração antes.

    A guarda por `information_schema` não é cosmética: `ALTER COLUMN ... TYPE`
    reescreve a tabela inteira sob ACCESS EXCLUSIVE. Sem ela, todo boot da API
    travaria as duas tabelas de autenticação.
    """
    grupos = [
        # (tabela, coluna, fuso de origem do valor já gravado)
        ("refreshtokens", "expires_at", "UTC"),
        ("refreshtokens", "created_at", None),
        ("refreshtokens", "revoked_at", None),
        ("passwordresetcodes", "expires_at", "UTC"),
        ("passwordresetcodes", "created_at", None),
        ("passwordresetcodes", "token_consumido_em", None),
    ]
    with get_db_cursor(commit=True) as cur:
        for tabela, coluna, fuso in grupos:
            cur.execute(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
                """,
                (tabela, coluna),
            )
            row = cur.fetchone()
            if not row or row["data_type"] != "timestamp without time zone":
                continue  # já convertida, ou coluna ainda não existe
            origem = "'UTC'" if fuso == "UTC" else "current_setting('TimeZone')"
            cur.execute(
                f"ALTER TABLE {tabela} ALTER COLUMN {coluna} "
                f"TYPE timestamptz USING {coluna} AT TIME ZONE {origem}"
            )


def ensure_timestamptz_restante():
    """Converte as demais colunas de data do schema para TIMESTAMPTZ.

    Complementa `ensure_timestamptz_tokens`, que tratou só as tabelas de token.
    Aqui a conversão é mais simples porque a semântica NÃO estava mista: todas
    estas colunas são escritas exclusivamente por `NOW()`/`CURRENT_TIMESTAMP`
    (verificado caso a caso — inclusive `data_associacao`, que passa `NOW()` no
    template do execute_values, e `consentimento_data`/`revogado_em`, que saem
    de CURRENT_TIMESTAMP em repositories/rostos.py). Fonte única significa que
    todas guardam hora de PAREDE da sessão, e todas usam a mesma cláusula.

    Usar `AT TIME ZONE 'UTC'` aqui, como nas colunas de token, deslocaria tudo
    pelo offset do fuso do banco — que em produção é America/Sao_Paulo, não UTC.

    Efeito visível: `consentimento_data`, `revogado_em` e `registrado_em` saem
    para o cliente via `.isoformat()` e passam a levar offset. Os dois
    consumidores no app fazem `new Date(...).toLocaleString('pt-BR')`, que hoje
    acerta por coincidência (string naive lida como hora local, device no mesmo
    fuso) e passa a acertar de fato, inclusive fora do Brasil.

    Mesma guarda por `information_schema` do outro: `ALTER COLUMN ... TYPE`
    reescreve a tabela sob ACCESS EXCLUSIVE, e sem ela todo boot travaria
    Usuarios, Presencas e Colecao_Rostos.
    """
    colunas = [
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
    with get_db_cursor(commit=True) as cur:
        for tabela, coluna in colunas:
            cur.execute(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
                """,
                (tabela, coluna),
            )
            row = cur.fetchone()
            if not row or row["data_type"] != "timestamp without time zone":
                continue  # já convertida, ou coluna/tabela ainda não existe
            cur.execute(
                f"ALTER TABLE {tabela} ALTER COLUMN {coluna} "
                f"TYPE timestamptz USING {coluna} AT TIME ZONE current_setting('TimeZone')"
            )


_ETAPAS = [
    "ensure_base_schema",
    "ensure_professor_departamento_dropped",
    "ensure_chamada_professor_nullable",
    "ensure_refresh_tokens_table",
    "ensure_lgpd_columns",
    "ensure_multi_angle_faces",
    "ensure_push_tokens_table",
    "ensure_push_receipts_table",
    "ensure_primeiro_acesso_column",
    "ensure_reset_codes_table",
    "ensure_reset_token_consumo",
    # Depois das duas tabelas existirem e de token_consumido_em ter sido criada.
    "ensure_timestamptz_tokens",
    "ensure_rate_limit_table",
    "ensure_login_attempts_table",
    "ensure_camera_tokens_table",
    "ensure_presenca_por_aula",
    "ensure_chamada_aberta_unica",
    "ensure_indices_filtros_alunos",
    "ensure_indices_performance",
    "ensure_consentimentos_table",
    # Por último: depende de todas as tabelas e colunas acima já existirem.
    "ensure_timestamptz_restante",
]


def _apply_all():
    for nome in _ETAPAS:
        try:
            globals()[nome]()
        except Exception as e:
            # Sem o nome, o journal mostra só um traceback de psycopg2 e não diz
            # qual etapa quebrou.
            raise RuntimeError(f"Migration {nome} falhou: {e}") from e


def run_all():
    """Aplica schema base + migrações, serializado entre workers via advisory lock.

    Com -w 4 no gunicorn, os 4 workers chamam isto no startup ao mesmo tempo.
    O advisory lock garante execução sequencial; as funções são idempotentes,
    então os workers seguintes só confirmam que está tudo no lugar (sem race em
    CREATE TABLE/TYPE — antes dava `duplicate key pg_type_typname_nsp_index`).

    Qualquer falha aborta o boot (RuntimeError). Schema incompleto com a API no
    ar gera 500s aleatórios longe da causa — preferimos não subir.
    """
    lock_conn = _db.get_db_connection()
    if lock_conn is None:
        raise RuntimeError("Migrations: sem conexão com o banco; schema não aplicado.")
    try:
        with lock_conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(%s)", (_MIGRATION_LOCK_KEY,))
        lock_conn.commit()

        _apply_all()
    finally:
        try:
            with lock_conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (_MIGRATION_LOCK_KEY,))
            lock_conn.commit()
        except Exception:
            pass
        _db.release_connection(lock_conn)
