from infra.database import get_db_cursor


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
