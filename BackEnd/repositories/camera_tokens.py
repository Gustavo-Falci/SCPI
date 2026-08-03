"""Tokens de serviço da câmera, um por sala.

Persiste apenas o SHA-256 do token. O lookup é pelo hash do token apresentado,
então não há comparação de segredo em texto — comparação constant-time não se
aplica aqui.
"""
import hashlib
import secrets

from infra.database import DB_INDISPONIVEL, get_db_cursor


def hash_camera_token(token_plain: str) -> str:
    """Hash determinístico para lookup do token no banco."""
    return hashlib.sha256(token_plain.encode("utf-8")).hexdigest()


def buscar_sala_por_token(token_plain: str):
    """Devolve a sala do token ativo, None se desconhecido/revogado, ou
    DB_INDISPONIVEL se o banco não respondeu — os dois últimos casos têm
    semântica http diferente (403 vs 503) e não podem ser achatados juntos."""
    if not token_plain:
        return None
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return DB_INDISPONIVEL
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


def listar_tokens():
    """Metadados dos tokens, ou DB_INDISPONIVEL se o banco não respondeu.

    Nunca devolve o token nem o hash. A sentinela existe porque lista vazia
    também é resposta legítima: achatar as duas fazia o CLI anunciar "Nenhum
    token emitido" com o banco fora, e quem lê isso emite um token duplicado
    para uma sala que já tinha o dela.
    """
    with get_db_cursor() as cur:
        if not cur:
            return DB_INDISPONIVEL
        cur.execute(
            "SELECT id, sala, descricao, criado_em, ultimo_uso_em, revogado_em "
            "FROM camera_tokens ORDER BY sala, id"
        )
        return list(cur.fetchall())


def revogar_token(token_id: int):
    """True se revogou, False se não existe/já estava revogado, DB_INDISPONIVEL
    se o banco não respondeu.

    A distinção é de segurança, não de estética: com `False` para banco fora, o
    CLI dizia "não encontrado ou já revogado" — e quem está revogando um token
    comprometido lê isso como "já está seguro" e para de agir, com o token ainda
    válido no banco.
    """
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return DB_INDISPONIVEL
        cur.execute(
            "UPDATE camera_tokens SET revogado_em = NOW() "
            "WHERE id = %s AND revogado_em IS NULL RETURNING id",
            (token_id,),
        )
        return cur.fetchone() is not None
