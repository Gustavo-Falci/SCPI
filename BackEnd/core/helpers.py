import logging
import secrets
from typing import Optional

from fastapi import HTTPException, UploadFile

from infra.aws_clientes import s3_client
from core.config import BUCKET_NAME

logger = logging.getLogger("scpi.helpers")

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


def internal_error(exc: Exception, context: str = "unknown") -> HTTPException:
    """Loga internamente a exceção e devolve 500 genérico ao cliente (sem vazar stack)."""
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
