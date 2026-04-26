import logging

from infra.database import get_db_cursor

logger = logging.getLogger("scpi.migrations")


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
    except Exception as e:
        logger.error("Falha ao criar tabela PasswordResetCodes: %s", e)


def run_all():
    ensure_refresh_tokens_table()
    ensure_lgpd_columns()
    ensure_push_tokens_table()
    ensure_primeiro_acesso_column()
    ensure_reset_codes_table()
