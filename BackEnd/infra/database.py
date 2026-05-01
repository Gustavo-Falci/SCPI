# database.py
import os
import uuid
import threading

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import pool as _pgpool
    _IS_PSYCOPG2 = True
except ImportError:
    import pg8000.dbapi as psycopg2  # type: ignore
    _pgpool = None
    _IS_PSYCOPG2 = False

    class RealDictCursor:
        def __init__(self, conn):
            self.conn = conn

        @staticmethod
        def _row_factor(cursor, row):
            col_names = [d[0] for d in cursor.description]
            return dict(zip(col_names, row))

from contextlib import contextmanager
from dotenv import load_dotenv, find_dotenv
import logging

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


def _build_database_url() -> str:
    """Monta a URL do PostgreSQL a partir de variáveis de ambiente.

    Falha imediatamente se qualquer variável obrigatória estiver ausente.
    """
    from urllib.parse import quote_plus

    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        raise RuntimeError(
            f"Variáveis de ambiente obrigatórias não configuradas: {', '.join(missing)}. "
            "Configure-as no arquivo BackEnd/.env antes de iniciar a aplicação."
        )

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    user = quote_plus(os.getenv("DB_USER"))
    password = quote_plus(os.getenv("DB_PASSWORD"))
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


_pool = None
_pool_lock = threading.Lock()


def _ensure_pool():
    """Inicializa pool de conexão (lazy, threadsafe). Retorna None se pg8000."""
    if not _IS_PSYCOPG2:
        return None

    global _pool
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        minconn = int(os.getenv("DB_POOL_MIN", "1"))
        maxconn = int(os.getenv("DB_POOL_MAX", "10"))

        try:
            _pool = _pgpool.ThreadedConnectionPool(
                minconn,
                maxconn,
                dsn=_build_database_url(),
                options="-c timezone=America/Sao_Paulo",
            )
            logger.info("Pool de conexão criado (min=%s, max=%s)", minconn, maxconn)
        except Exception as e:
            logger.error("Falha ao criar pool de conexão: %s", e)
            _pool = None

        return _pool


def close_pool():
    """Fecha todas as conexões do pool (chamar no shutdown da app)."""
    global _pool
    if _pool is not None:
        try:
            _pool.closeall()
            logger.info("Pool de conexão encerrado.")
        except Exception as e:
            logger.error("Erro ao fechar pool: %s", e)
        finally:
            _pool = None


def get_db_connection():
    """Retorna uma conexão do pool, ou crua se pool indisponível.

    Mantém contrato antigo: retorna None em caso de erro.
    Importante: se a conexão veio do pool, deve ser devolvida via
    `release_connection(conn)` em vez de `conn.close()`.
    """
    pool = _ensure_pool()
    if pool is not None:
        try:
            return pool.getconn()
        except Exception as e:
            logger.error("Falha ao obter conexão do pool: %s", e)
            return None

    # Fallback (pg8000 ou pool falhou)
    try:
        conn = psycopg2.connect(_build_database_url())
        with conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'America/Sao_Paulo'")
        conn.commit()
        return conn
    except Exception as e:
        logger.error("Erro de conexão PostgreSQL: %s", e)
        return None


def release_connection(conn, broken: bool = False) -> None:
    """Devolve a conexão ao pool, ou fecha se foi obtida fora dele."""
    if conn is None:
        return
    pool = _pool
    if pool is not None:
        try:
            pool.putconn(conn, close=broken)
        except Exception as e:
            logger.error("Falha ao devolver conexão ao pool: %s", e)
            try:
                conn.close()
            except Exception:
                pass
    else:
        try:
            conn.close()
        except Exception:
            pass


@contextmanager
def get_db_cursor(commit=False):
    """Gerenciador de contexto para operações de banco.

    Uso:
        with get_db_cursor() as cur:
            cur.execute(...)
    """
    conn = get_db_connection()
    if not conn:
        yield None
        return

    if _IS_PSYCOPG2:
        raw_cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        raw_cursor = conn.cursor()

    class DictCursorWrapper:
        def __init__(self, cur):
            self.cur = cur

        def execute(self, *args, **kwargs):
            self.cur.execute(*args, **kwargs)
            return self

        def fetchone(self):
            row = self.cur.fetchone()
            if row is None:
                return None
            return self._to_dict(row)

        def fetchall(self):
            rows = self.cur.fetchall()
            return [self._to_dict(row) for row in rows]

        def _to_dict(self, row):
            if not getattr(self.cur, "description", None):
                return row
            cols = [desc[0] for desc in self.cur.description]
            return {cols[i]: (str(val) if isinstance(val, uuid.UUID) else val) for i, val in enumerate(row)}

        @property
        def rowcount(self):
            return getattr(self.cur, "rowcount", -1)

        def close(self):
            self.cur.close()

    cursor = raw_cursor if _IS_PSYCOPG2 else DictCursorWrapper(raw_cursor)
    broken = False
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            broken = True
        logger.error("Erro na transação: %s", e)
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        release_connection(conn, broken=broken)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logger.info("Testando conexão com o banco...")
    try:
        with get_db_cursor() as cur:
            if cur:
                cur.execute("SELECT version();")
                db_version = cur.fetchone()
                logger.info(f"Conectado com sucesso! Versão do BD: {db_version}")
            else:
                logger.error("Falha na conexão: cursor None. Verifique .env.")
    except Exception as e:
        logger.error(f"Erro ao tentar conectar: {e}")
    finally:
        close_pool()
