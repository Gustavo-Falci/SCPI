"""Tokens de serviço da câmera, um por sala.

Persiste apenas o SHA-256 do token. O lookup é pelo hash do token apresentado,
então não há comparação de segredo em texto — comparação constant-time não se
aplica aqui.
"""
import hashlib
import secrets

from infra.database import get_db_cursor


def hash_camera_token(token_plain: str) -> str:
    """Hash determinístico para lookup do token no banco."""
    return hashlib.sha256(token_plain.encode("utf-8")).hexdigest()


def buscar_sala_por_token(token_plain: str) -> str | None:
    """Devolve a sala do token ativo, ou None se desconhecido ou revogado."""
    if not token_plain:
        return None
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute(
            """
            UPDATE camera_tokens
               SET ultimo_uso_em = NOW()
             WHERE token_hash = %s AND revogado_em IS NULL
            RETURNING sala
            """,
            (hash_camera_token(token_plain),),
        )
        row = cur.fetchone()
        return row["sala"] if row else None


def emitir_token(sala: str, descricao: str | None = None) -> str:
    """Cria um token para a sala e devolve o texto puro — a única vez que ele existe."""
    token_plain = secrets.token_urlsafe(48)
    with get_db_cursor(commit=True) as cur:
        if not cur:
            raise RuntimeError("Banco indisponível para emitir token.")
        cur.execute(
            "INSERT INTO camera_tokens (sala, token_hash, descricao) VALUES (%s, %s, %s)",
            (sala, hash_camera_token(token_plain), descricao),
        )
    return token_plain


def listar_tokens() -> list:
    """Metadados dos tokens. Nunca devolve o token nem o hash."""
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            "SELECT id, sala, descricao, criado_em, ultimo_uso_em, revogado_em "
            "FROM camera_tokens ORDER BY sala, id"
        )
        return list(cur.fetchall())


def revogar_token(token_id: int) -> bool:
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute(
            "UPDATE camera_tokens SET revogado_em = NOW() "
            "WHERE id = %s AND revogado_em IS NULL RETURNING id",
            (token_id,),
        )
        return cur.fetchone() is not None
