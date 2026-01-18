# database.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
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
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT'),
            cursor_factory=RealDictCursor
        )
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