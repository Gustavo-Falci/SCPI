import logging

from infra.database import get_db_cursor

logger = logging.getLogger("scpi.auth_lockout")

# Lockout de login por conta (B1). Complementa o rate-limit por IP: pega
# brute-force distribuído entre IPs contra um email-alvo.
MAX_FAILS = 8
WINDOW_MINUTES = 15
LOCK_MINUTES = 15


def esta_bloqueado(email):
    """Retorna locked_until se a conta está travada agora, senão None. Fail-open."""
    with get_db_cursor() as cur:
        if not cur:
            return None
        try:
            cur.execute(
                "SELECT locked_until FROM login_attempts "
                "WHERE email=%s AND locked_until > now()",
                (email,),
            )
            row = cur.fetchone()
        except Exception as e:
            logger.warning("esta_bloqueado fail-open: %s", e)
            return None
    return row["locked_until"] if row else None


def registrar_falha(email, max_fails=MAX_FAILS, window_minutes=WINDOW_MINUTES,
                    lock_minutes=LOCK_MINUTES):
    """Conta uma falha de login (upsert atômico) e trava ao atingir o limite.

    Fixed-window por conta: se a última janela (`first_fail_at`) expirou, reinicia
    a contagem em 1. Ao alcançar `max_fails`, seta `locked_until`. Retorna
    (fails, locked_until). Fail-open: erro de DB retorna (0, None).
    """
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return (0, None)
        try:
            cur.execute(
                """
                INSERT INTO login_attempts AS la (email, fails, first_fail_at, locked_until)
                VALUES (%(email)s, 1, now(), NULL)
                ON CONFLICT (email) DO UPDATE SET
                    fails = CASE
                        WHEN la.first_fail_at < now() - make_interval(mins => %(window)s)
                            THEN 1
                        ELSE la.fails + 1 END,
                    first_fail_at = CASE
                        WHEN la.first_fail_at < now() - make_interval(mins => %(window)s)
                            THEN now()
                        ELSE la.first_fail_at END,
                    locked_until = CASE
                        WHEN (CASE
                                WHEN la.first_fail_at < now() - make_interval(mins => %(window)s)
                                    THEN 1
                                ELSE la.fails + 1 END) >= %(max)s
                            THEN now() + make_interval(mins => %(lock)s)
                        ELSE la.locked_until END
                RETURNING fails, locked_until
                """,
                {"email": email, "window": window_minutes, "max": max_fails,
                 "lock": lock_minutes},
            )
            row = cur.fetchone()
        except Exception as e:
            logger.warning("registrar_falha fail-open: %s", e)
            return (0, None)
    return (row["fails"], row["locked_until"]) if row else (0, None)


def limpar_falhas(email):
    """Zera o estado de lockout no login bem-sucedido."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return
        try:
            cur.execute("DELETE FROM login_attempts WHERE email=%s", (email,))
        except Exception as e:
            logger.warning("limpar_falhas falhou: %s", e)


def purgar_login_attempts():
    """Remove registros antigos já desbloqueados. Ciclo diário do agendador."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute(
            "DELETE FROM login_attempts "
            "WHERE (locked_until IS NULL OR locked_until < now()) "
            "AND first_fail_at < now() - make_interval(days => 1)"
        )
        return cur.rowcount
