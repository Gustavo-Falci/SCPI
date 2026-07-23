import logging
import time

from limits.storage import Storage

from infra.database import get_db_cursor

logger = logging.getLogger("scpi.limiter")


class PostgresStorage(Storage):
    """Storage fixed-window do slowapi/limits em Postgres, compartilhado entre workers.

    Motivação (M4): com `gunicorn -w 4` o storage in-memory mantém um contador por
    worker, multiplicando o limite efetivo por ~4. Aqui o contador vive no Postgres,
    único para todos os workers.

    Fail-open: qualquer erro/queda de DB libera o request (valor permissivo) — um
    blip de banco não pode transformar todo endpoint com rate-limit em 500.
    """

    STORAGE_SCHEME = ["scpi-postgres"]

    def __init__(self, uri=None, **options):
        super().__init__(uri, **options)

    @property
    def base_exceptions(self):
        # Erros tratados internamente (fail-open); a lib nunca precisa envolvê-los.
        return Exception

    def incr(self, key, expiry, amount=1):
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return amount  # fail-open: início de janela
            try:
                cur.execute(
                    """
                    INSERT INTO rate_limit_buckets (key, count, expires_at)
                    VALUES (%s, %s, now() + make_interval(secs => %s))
                    ON CONFLICT (key) DO UPDATE SET
                        count = CASE
                            WHEN rate_limit_buckets.expires_at < now() THEN %s
                            ELSE rate_limit_buckets.count + %s END,
                        expires_at = CASE
                            WHEN rate_limit_buckets.expires_at < now()
                                THEN now() + make_interval(secs => %s)
                            ELSE rate_limit_buckets.expires_at END
                    RETURNING count
                    """,
                    (key, amount, expiry, amount, amount, expiry),
                )
                row = cur.fetchone()
            except Exception as e:
                logger.warning("limiter incr fail-open: %s", e)
                return amount
        return int(row["count"]) if row else amount

    def get(self, key):
        with get_db_cursor() as cur:
            if not cur:
                return 0
            try:
                cur.execute(
                    "SELECT count FROM rate_limit_buckets "
                    "WHERE key=%s AND expires_at >= now()",
                    (key,),
                )
                row = cur.fetchone()
            except Exception as e:
                logger.warning("limiter get fail-open: %s", e)
                return 0
        return int(row["count"]) if row else 0

    def get_expiry(self, key):
        with get_db_cursor() as cur:
            if not cur:
                return time.time()
            try:
                cur.execute(
                    "SELECT EXTRACT(EPOCH FROM expires_at) AS exp FROM rate_limit_buckets "
                    "WHERE key=%s AND expires_at >= now()",
                    (key,),
                )
                row = cur.fetchone()
            except Exception as e:
                logger.warning("limiter get_expiry fail-open: %s", e)
                return time.time()
        return float(row["exp"]) if row else time.time()

    def check(self):
        with get_db_cursor() as cur:
            if not cur:
                return False
            try:
                cur.execute("SELECT 1")
                cur.fetchone()
                return True
            except Exception:
                return False

    def reset(self):
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return None
            cur.execute("DELETE FROM rate_limit_buckets")
            return cur.rowcount

    def clear(self, key):
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return
            cur.execute("DELETE FROM rate_limit_buckets WHERE key=%s", (key,))


def purgar_rate_limit_buckets():
    """Remove janelas expiradas. Chamado no ciclo diário do agendador."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute("DELETE FROM rate_limit_buckets WHERE expires_at < now()")
        return cur.rowcount
