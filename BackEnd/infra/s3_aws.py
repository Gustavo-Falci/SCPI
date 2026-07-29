"""Listagem paginada do bucket de rostos.

Arquivo separado de aws_clientes.py de propósito: lá só se instanciam clientes
boto3; aqui mora operação sobre o bucket, espelhando o que rekognition_aws.py já
faz para a collection.
"""
import logging

from core.config import BUCKET_NAME
from infra.aws_clientes import s3_client

logger = logging.getLogger(__name__)

# Mesmo raciocínio do teto no Rekognition: 50 páginas de 1000 cobrem 50 mil
# objetos e impedem que uma resposta malformada pendure o request.
MAX_PAGINAS = 50


def listar_todos_objetos_s3(prefixo: str = "alunos/") -> tuple[list[dict], bool]:
    """Lista todos os objetos sob o prefixo, seguindo ContinuationToken até o fim.

    Devolve (objetos, completo). completo=False quando o cliente não existe, a AWS
    falhou ou o teto de páginas foi atingido.
    """
    if not s3_client:
        logger.error("❌ Cliente S3 não inicializado. Listagem cancelada.")
        return [], False

    objetos: list[dict] = []
    token = None
    try:
        for _ in range(MAX_PAGINAS):
            kwargs = {"Bucket": BUCKET_NAME, "Prefix": prefixo}
            if token:
                kwargs["ContinuationToken"] = token
            resposta = s3_client.list_objects_v2(**kwargs)
            for obj in resposta.get("Contents", []):
                key = obj.get("Key", "")
                # Chave terminada em '/' é marcador de pasta, não arquivo.
                if not key or key.endswith("/"):
                    continue
                last_modified = obj.get("LastModified")
                objetos.append({
                    "key": key,
                    "size": obj.get("Size", 0),
                    "last_modified": last_modified.isoformat() if last_modified else None,
                })
            token = resposta.get("NextContinuationToken")
            if not resposta.get("IsTruncated") or not token:
                return objetos, True
        logger.warning("⚠️ Listagem do S3 atingiu o teto de %s páginas.", MAX_PAGINAS)
        return objetos, False
    except Exception as e:
        logger.error(f"❌ Falha ao listar objetos do bucket: {e}")
        return [], False
