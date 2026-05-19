import logging
import secrets
from typing import Optional

from fastapi import HTTPException, UploadFile
from psycopg2 import errors as pg_errors

from infra.aws_clientes import s3_client
from core.config import BUCKET_NAME

logger = logging.getLogger("scpi.helpers")

# Mapeamento de constraints UNIQUE para mensagens orientadas ao usuário final.
# Constraint name é o nome real do índice/constraint no Postgres; quando uma
# nova constraint for adicionada, lembrar de estender este mapa para evitar
# cair no fallback genérico.
_UNIQUE_CONSTRAINT_MESSAGES: dict[str, str] = {
    "usuarios_email_key": "Já existe um usuário com este e-mail.",
    "alunos_ra_key": "Já existe um aluno com este RA.",
    "alunos_usuario_id_key": "Este usuário já está cadastrado como aluno.",
    "professores_usuario_id_key": "Este usuário já está cadastrado como professor.",
    "turmas_codigo_turma_key": "Já existe uma turma com este código.",
    "turma_alunos_turma_id_aluno_id_key": "Aluno já matriculado nesta turma.",
    "colecao_rostos_external_image_id_key": "Rosto já cadastrado para este aluno.",
    "presencas_chamada_id_aluno_id_key": "Presença já registrada para este aluno.",
    "presencas_chamada_aluno_aula_key": "Presença já registrada para esta aula.",
    "uq_chamada_aberta_por_turma": "Já existe uma chamada aberta para esta turma.",
}

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png"}

# Assinaturas iniciais ("magic bytes") aceitas por tipo MIME real.
# Evita upload de executáveis renomeados como .png/.jpg (manual §3.1).
_IMAGE_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


def mask_email(email: str) -> str:
    """Mascara email para logs: 'gu.falci@gmail.com' -> 'g***@gmail.com'."""
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def _detect_image_mime(header: bytes) -> Optional[str]:
    """Identifica tipo de imagem a partir dos primeiros bytes; None se não suportado."""
    for mime, signatures in _IMAGE_MAGIC_SIGNATURES.items():
        if any(header.startswith(sig) for sig in signatures):
            return mime
    return None


async def validate_image_upload(foto: UploadFile) -> bytes:
    """Valida content-type declarado, magic bytes reais e tamanho da imagem."""
    if foto.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(status_code=400, detail="Apenas imagens JPEG ou PNG são permitidas.")
    content = await foto.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo de imagem vazio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Imagem muito grande (limite: 5 MB).")

    real_mime = _detect_image_mime(content[:16])
    if real_mime is None:
        raise HTTPException(
            status_code=400,
            detail="Conteúdo do arquivo não corresponde a uma imagem JPEG ou PNG válida.",
        )
    declared = "image/jpeg" if foto.content_type == "image/jpg" else foto.content_type
    if real_mime != declared:
        logger.warning(
            "Upload rejeitado: content-type declarado=%s diverge do conteúdo real=%s",
            foto.content_type, real_mime,
        )
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo declarado não corresponde ao conteúdo real.",
        )
    return content


def _unique_violation_message(exc: pg_errors.UniqueViolation) -> str:
    constraint = getattr(getattr(exc, "diag", None), "constraint_name", "") or ""
    return _UNIQUE_CONSTRAINT_MESSAGES.get(constraint, "Já existe um registro com estes dados.")


def internal_error(exc: Exception, context: str = "unknown") -> HTTPException:
    """Loga internamente a exceção e devolve resposta apropriada ao cliente.

    Erros de banco com semântica conhecida (UNIQUE/FK violations) são
    traduzidos em 409/400 com mensagem amigável. O resto vira 500 genérico
    para evitar vazamento de detalhes internos (stack, SQL, etc.).
    """
    if isinstance(exc, pg_errors.UniqueViolation):
        msg = _unique_violation_message(exc)
        logger.info("Conflito de unicidade em %s: %s", context, msg)
        return HTTPException(
            status_code=409,
            detail={"detail": msg, "error_code": "UNIQUE_VIOLATION"},
        )
    if isinstance(exc, pg_errors.ForeignKeyViolation):
        logger.info("FK violation em %s: %s", context, exc)
        return HTTPException(
            status_code=400,
            detail={
                "detail": "Referência inválida: um dos registros vinculados não existe.",
                "error_code": "FOREIGN_KEY_VIOLATION",
            },
        )
    if isinstance(exc, pg_errors.CheckViolation):
        logger.info("Check violation em %s: %s", context, exc)
        return HTTPException(
            status_code=400,
            detail={
                "detail": "Dados inválidos para esta operação.",
                "error_code": "CHECK_VIOLATION",
            },
        )
    logger.exception("Erro interno em %s: %s", context, exc)
    return HTTPException(status_code=500, detail="Erro interno do servidor.")


def gerar_senha_temporaria() -> str:
    return secrets.token_urlsafe(9)


def gerar_url_presigned(s3_key: str, expira_segundos: int = 300) -> Optional[str]:
    """Gera URL pré-assinada do S3, ou None se falhar."""
    if not s3_client or not BUCKET_NAME:
        return None
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expira_segundos,
        )
    except Exception as e:
        logger.warning("Falha ao gerar presigned URL para %s: %s", s3_key, e)
        return None
