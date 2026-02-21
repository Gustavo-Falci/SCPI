# database.py
import os
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    import pg8000.dbapi as psycopg2
    class RealDictCursor:
        def __init__(self, conn):
            self.conn = conn
        
        @staticmethod
        def _row_factor(cursor, row):
             col_names = [d[0] for d in cursor.description]
             return dict(zip(col_names, row))

from contextlib import contextmanager
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def get_db_connection():
    """Cria uma conexão crua com o banco."""
    try:
        conn = psycopg2.connect(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME')
        )

        # Se for pg8000 (psycopg2 fake), não suporta cursor_factory no connect
        # Mas vamos lidar com Dicts manualmente se precisar ou usar wrapper
        # Para simplificar, se for pg8000, usamos fetchall e convertemos
        return conn
    except Exception as e:
        logger.error(f"Erro de conexão PostgreSQL: {e}")
        return None

@contextmanager
def get_db_cursor(commit=False):
    """
    Gerenciador de contexto para operações de banco.
    Uso:
        with get_db_cursor() as cur:
            cur.execute(...)
    """
    conn = get_db_connection()
    if not conn:
        yield None
        return

    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro na transação: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logger.info("Testando conexão com o banco na Oracle Cloud...")
    try:
        # Aproveitando o seu novo context manager
        with get_db_cursor() as cur:
            if cur:
                cur.execute("SELECT version();")
                db_version = cur.fetchone()
                logger.info(f"Conectado com sucesso! Versão do BD: {db_version}")
            else:
                logger.error("Falha na conexão: O cursor retornou None. Verifique o IP, porta e credenciais no seu arquivo .env.")
    except Exception as e:
        logger.error(f"Erro ao tentar conectar: {e}")