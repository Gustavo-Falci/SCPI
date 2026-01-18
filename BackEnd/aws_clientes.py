import logging

import boto3
from botocore.exceptions import ClientError
from config import AWS_REGION

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s (aws_clients): %(message)s")
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


def verificar_conexao_rekognition():
    """
    Verifica a conexão com o AWS Rekognition listando coleções.
    Retorna True se a conexão for bem-sucedida, False caso contrário.
    """
    if not rekognition_client:
        logger.error("Cliente Rekognition não inicializado.")
        return False

    try:
        rekognition_client.list_collections(MaxResults=1)  # Teste leve
        logger.info("Conexão com AWS Rekognition verificada com sucesso.")
        return True

    except ClientError as e:
        logger.error(f"Erro ao verificar conexão com Rekognition: {e.response['Error']['Message']}")
        return False

    except Exception as e:
        logger.error(f"Erro inesperado ao verificar conexão com Rekognition: {e}")
        return False


def verificar_conexao_s3():
    """
    Verifica a conexão com o AWS S3 listando buckets (limitado).
    Retorna True se a conexão for bem-sucedida, False caso contrário.
    """
    if not s3_client:
        logger.error("Cliente S3 não inicializado.")
        return False

    try:
        s3_client.list_buckets()  # Verifica se consegue listar buckets (requer permissão)
        logger.info("Conexão com AWS S3 verificada com sucesso.")
        return True

    except ClientError as e:
        logger.error(f"Erro ao verificar conexão com S3: {e.response['Error']['Message']}")
        return False

    except Exception as e:
        logger.error(f"Erro inesperado ao verificar conexão com S3: {e}")
        return False


# Exemplo de como executar um teste de conexão se este arquivo for rodado diretamente
if __name__ == "__main__":
    logger.info("Testando conexões com AWS...")
    if rekognition_client:
        verificar_conexao_rekognition()

    else:
        logger.warning("Cliente Rekognition não está disponível para teste.")

    if s3_client:
        verificar_conexao_s3()

    else:
        logger.warning("Cliente S3 não está disponível para teste.")
