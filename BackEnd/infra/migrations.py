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
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Usuarios (
                    usuario_id uuid PRIMARY KEY,
                    nome varchar(255) NOT NULL,
                    email varchar(255) NOT NULL UNIQUE,
                    senha varchar(255) NOT NULL,
                    tipo_usuario varchar(50) NOT NULL,
                    data_cadastro timestamp DEFAULT CURRENT_TIMESTAMP
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
                    data_associacao timestamp DEFAULT CURRENT_TIMESTAMP,
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
                    professor_id uuid NOT NULL
                        REFERENCES Professores(professor_id) ON DELETE CASCADE,
                    data_chamada date NOT NULL,
                    horario_inicio time NOT NULL,
                    horario_fim time,
                    status varchar(50) DEFAULT 'Aberta',
                    data_criacao timestamp DEFAULT CURRENT_TIMESTAMP
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
                    hora_registro timestamp DEFAULT CURRENT_TIMESTAMP,
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
                    data_indexacao timestamp DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
    except Exception as e:
        logger.error("Falha ao aplicar schema base: %s", e)


def ensure_professor_departamento_dropped():
    """Remove a coluna departamento de Professores (idempotente).

    Campo cosmético sem uso em nenhuma regra de negócio. Produção não tinha
    dado preenchido, então o DROP não perde informação relevante.
    """
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "ALTER TABLE Professores DROP COLUMN IF EXISTS departamento"
            )
    except Exception as e:
        logger.error("Falha ao remover coluna departamento: %s", e)


def ensure_lgpd_columns():
    """Adiciona colunas de consentimento/revogação de biometria (idempotente)."""
    try:
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
                ADD COLUMN IF NOT EXISTS consentimento_data TIMESTAMP NULL
                """
            )
            cur.execute(
                """
                ALTER TABLE Colecao_Rostos
                ADD COLUMN IF NOT EXISTS revogado_em TIMESTAMP NULL
                """
            )
    except Exception as e:
        logger.error("Falha ao aplicar colunas LGPD: %s", e)


def ensure_refresh_tokens_table():
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS RefreshTokens (
                    token_hash VARCHAR(128) PRIMARY KEY,
                    usuario_id VARCHAR(64) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    revoked_at TIMESTAMP NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_refresh_usuario ON RefreshTokens (usuario_id)"
            )
    except Exception as e:
        logger.error("Falha ao criar tabela RefreshTokens: %s", e)


def ensure_push_tokens_table():
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS PushTokens (
                    usuario_id VARCHAR(64) PRIMARY KEY,
                    expo_token TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
    except Exception as e:
        logger.error("Falha ao criar tabela PushTokens: %s", e)


def ensure_primeiro_acesso_column():
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                ALTER TABLE Usuarios
                ADD COLUMN IF NOT EXISTS primeiro_acesso BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
    except Exception as e:
        logger.error("Falha ao aplicar coluna primeiro_acesso: %s", e)


def ensure_reset_codes_table():
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS PasswordResetCodes (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    code VARCHAR(6) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
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
    except Exception as e:
        logger.error("Falha ao criar tabela PasswordResetCodes: %s", e)


def ensure_presenca_por_aula():
    """Adiciona total_aulas em chamadas e num_aula em presencas (idempotente)."""
    try:
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
    except Exception as e:
        logger.error("Falha ao aplicar migração presenca_por_aula: %s", e)


def ensure_multi_angle_faces():
    try:
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
    except Exception as e:
        logger.error("Falha ao aplicar migração multi-angle: %s", e)


def ensure_chamada_aberta_unica():
    """Garante no máximo uma chamada com status='Aberta' por turma (defesa contra race condition)."""
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_chamada_aberta_por_turma
                ON Chamadas (turma_id)
                WHERE status = 'Aberta'
                """
            )
    except Exception as e:
        logger.error("Falha ao aplicar índice único de chamadas abertas: %s", e)


def _apply_all():
    ensure_base_schema()
    ensure_professor_departamento_dropped()
    ensure_refresh_tokens_table()
    ensure_lgpd_columns()
    ensure_multi_angle_faces()
    ensure_push_tokens_table()
    ensure_primeiro_acesso_column()
    ensure_reset_codes_table()
    ensure_presenca_por_aula()
    ensure_chamada_aberta_unica()


def run_all():
    """Aplica schema base + migrações, serializado entre workers via advisory lock.

    Com -w 4 no gunicorn, os 4 workers chamam isto no startup ao mesmo tempo.
    O advisory lock garante execução sequencial; as funções são idempotentes,
    então os workers seguintes só confirmam que está tudo no lugar (sem race em
    CREATE TABLE/TYPE — antes dava `duplicate key pg_type_typname_nsp_index`).
    """
    lock_conn = _db.get_db_connection()
    if lock_conn is None:
        logger.error("Migrations: sem conexão com o banco; schema não aplicado.")
        return
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
