import logging
import secrets
from typing import Optional

from fastapi import HTTPException, UploadFile

from infra.aws_clientes import s3_client
from core.config import BUCKET_NAME

logger = logging.getLogger("scpi.helpers")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png"}


def mask_email(email: str) -> str:
    """Mascara email para logs: 'gu.falci@gmail.com' -> 'g***@gmail.com'."""
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


async def validate_image_upload(foto: UploadFile) -> bytes:
    """Valida content-type e tamanho da imagem, retornando os bytes já lidos."""
    if foto.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(status_code=400, detail="Apenas imagens JPEG ou PNG são permitidas.")
    content = await foto.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Imagem muito grande (limite: 5 MB).")
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo de imagem vazio.")
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
