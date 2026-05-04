import logging
import boto3
from botocore.exceptions import ClientError
from core.config import AWS_REGION

logger = logging.getLogger(__name__)

try:
    rekognition_client = boto3.client("rekognition", region_name=AWS_REGION)
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    logger.info(f"Clientes Rekognition e S3 inicializados para a região {AWS_REGION}.")

except ClientError as e:
    logger.error(f"Falha ao inicializar clientes AWS: {e.response['Error']['Message']}")
    # Em uma aplicação real, você pode querer levantar a exceção ou ter um mecanismo de fallback.
    rekognition_client = None
    s3_client = None

except Exception as e:
    logger.error(f"Erro inesperado durante a inicialização dos clientes AWS: {e}")
    rekognition_client = None
    s3_client = None


