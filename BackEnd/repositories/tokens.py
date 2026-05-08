from infra.database import get_db_cursor


def inserir_refresh_token(token_hash, usuario_id, expires_at):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute(
            """
            INSERT INTO RefreshTokens (token_hash, usuario_id, expires_at)
            VALUES (%s, %s, %s)
            """,
            (token_hash, usuario_id, expires_at),
        )
        return True


def rotacionar_refresh_token(token_hash_antigo, token_hash_novo, expires_at_novo):
    """Valida o token antigo, revoga e insere novo. Retorna a linha original ou None."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT rt.usuario_id, rt.expires_at, rt.revoked_at,
                   u.email, u.tipo_usuario
            FROM RefreshTokens rt
            JOIN Usuarios u ON u.usuario_id::text = rt.usuario_id
            WHERE rt.token_hash = %s
            """,
            (token_hash_antigo,),
        )
        row = cur.fetchone()
        if not row or row.get("revoked_at") is not None:
            return {"_status": "invalid"}

        import datetime as _dt
        if row["expires_at"] < _dt.datetime.utcnow():
            return {"_status": "expired"}

        cur.execute(
            "UPDATE RefreshTokens SET revoked_at = CURRENT_TIMESTAMP WHERE token_hash = %s",
            (token_hash_antigo,),
        )
        cur.execute(
            "INSERT INTO RefreshTokens (token_hash, usuario_id, expires_at) VALUES (%s, %s, %s)",
            (token_hash_novo, row["usuario_id"], expires_at_novo),
        )
        return {"_status": "ok", "row": row}


def revogar_refresh_token(token_hash, usuario_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute(
            """
            UPDATE RefreshTokens
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE token_hash = %s AND usuario_id = %s AND revoked_at IS NULL
            """,
            (token_hash, usuario_id),
        )
        return cur.rowcount


def purgar_tokens_expirados():
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute("DELETE FROM RefreshTokens WHERE expires_at < NOW()")
        return cur.rowcount


def invalidar_codigos_anteriores(email):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute("UPDATE PasswordResetCodes SET used = TRUE WHERE email = %s AND used = FALSE", (email,))
        return cur.rowcount


def inserir_codigo_reset(email, code, expires_at):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute(
            "INSERT INTO PasswordResetCodes (email, code, expires_at) VALUES (%s, %s, %s)",
            (email, code, expires_at),
        )
        return True


def substituir_codigo_reset(email, code, expires_at):
    """Invalida códigos anteriores e cria novo no mesmo commit."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute("UPDATE PasswordResetCodes SET used = TRUE WHERE email = %s AND used = FALSE", (email,))
        cur.execute(
            "INSERT INTO PasswordResetCodes (email, code, expires_at) VALUES (%s, %s, %s)",
            (email, code, expires_at),
        )
        return True


def buscar_codigo_reset_valido(email, codigo):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT id, expires_at FROM PasswordResetCodes
            WHERE email = %s AND code = %s AND used = FALSE
            ORDER BY created_at DESC LIMIT 1
            """,
            (email, codigo),
        )
        return cur.fetchone()


def marcar_codigo_reset_usado(codigo_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute("UPDATE PasswordResetCodes SET used = TRUE WHERE id = %s", (codigo_id,))
        return cur.rowcount
