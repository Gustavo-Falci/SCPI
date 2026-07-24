from infra.database import get_db_cursor
from psycopg2.extras import execute_values


def upsert_push_token(usuario_id, expo_token):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute(
            """
            INSERT INTO PushTokens (usuario_id, expo_token, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (usuario_id) DO UPDATE
                SET expo_token = EXCLUDED.expo_token,
                    updated_at = CURRENT_TIMESTAMP
            """,
            (usuario_id, expo_token),
        )
        return True


def obter_push_token_por_usuario(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT expo_token FROM PushTokens WHERE usuario_id = %s", (usuario_id,))
        return cur.fetchone()


def remover_push_token(expo_token):
    """Apaga um push token morto (DeviceNotRegistered). Por token, não por
    usuário: evita apagar um re-registro feito entre o envio e a poda.
    Ressalva: se a reinstalação reemitir o MESMO token (string idêntica), a
    deleção por token ainda remove a linha recém-criada; a janela do receipt
    (minutos a horas) amplia essa lacuna em relação ao caminho síncrono."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute("DELETE FROM PushTokens WHERE expo_token = %s", (expo_token,))
        return True


def registrar_tickets_pendentes(tickets):
    """Persiste tickets ok (id + token) para consulta de receipt depois.
    tickets = [{"id","token"}]. Idempotente por ticket_id."""
    if not tickets:
        return False
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        execute_values(
            cur,
            "INSERT INTO PushReceiptsPendentes (ticket_id, expo_token) VALUES %s "
            "ON CONFLICT (ticket_id) DO NOTHING",
            [(t["id"], t["token"]) for t in tickets],
        )
        return True


def listar_tickets_pendentes(idade_min_segundos, limite):
    """Tickets com receipt ainda não consultado e idade >= idade_min_segundos."""
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            "SELECT ticket_id, expo_token FROM PushReceiptsPendentes "
            "WHERE created_at <= NOW() - (%s * INTERVAL '1 second') "
            "ORDER BY created_at LIMIT %s",
            (idade_min_segundos, limite),
        )
        return cur.fetchall()


def remover_tickets_pendentes(ticket_ids):
    """Apaga tickets já processados (receipt recebido)."""
    if not ticket_ids:
        return 0
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute(
            "DELETE FROM PushReceiptsPendentes WHERE ticket_id = ANY(%s)",
            (list(ticket_ids),),
        )
        return cur.rowcount


def remover_tickets_pendentes_antigos(idade_max_segundos):
    """Apaga pendentes cujo receipt nunca chegou (deu-se por perdido)."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute(
            "DELETE FROM PushReceiptsPendentes "
            "WHERE created_at <= NOW() - (%s * INTERVAL '1 second')",
            (idade_max_segundos,),
        )
        return cur.rowcount
