from config import COLLECTION_ID, BUCKET_NAME  # Usa a configuração correta
from aws_clientes import rekognition_client
import botocore.exceptions
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

def criar_colecao():
    """Cria a coleção no Rekognition, se não existir."""
    if not rekognition_client:
        logger.error("❌ Cliente Rekognition não inicializado. Criação de coleção cancelada.")
        return None
    
    try:
        rekognition_client.describe_collection(CollectionId=COLLECTION_ID) # Usa o rekognition_client importado
        logger.info(f"A coleção '{COLLECTION_ID}' já existe.")
    except rekognition_client.exceptions.ResourceNotFoundException: # A exceção é do cliente

        try:
            response = rekognition_client.create_collection(CollectionId=COLLECTION_ID) # Usa o rekognition_client importado
            logger.info(f"✅ Coleção '{COLLECTION_ID}' criada com sucesso!")
            return response
        
        except botocore.exceptions.ClientError as e:
            logger.error(f"❌ Erro ao criar a coleção: {e.response['Error']['Message']}")
            return None
        
    # Adicionar tratamento para ClientError em describe_collection também
    except botocore.exceptions.ClientError as e:
        logger.error(f"❌ Erro ao descrever a coleção: {e.response['Error']['Message']}")
        return None


def cadastrar_rosto(s3_path, aluno_id):
    """Cadastra o rosto de um aluno a partir de uma imagem no S3."""
    if not rekognition_client:
        logger.error("❌ Cliente Rekognition não inicializado. Cadastro de rosto cancelado.")
        return None
    
    try:
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': s3_path}},
            ExternalImageId=aluno_id,
            DetectionAttributes=['ALL']
        )

        faces = response.get('FaceRecords', [])

        if len(faces) == 1:
            logging.info(f"✅ Rosto do aluno '{aluno_id}' cadastrado com sucesso!")

        elif len(faces) > 1:
            logging.warning(f"⚠️ Mais de um rosto detectado. Apenas o primeiro foi cadastrado para '{aluno_id}'.")

        else:
            logging.error("❌ Nenhum rosto detectado na imagem!")

        return response
    
    except botocore.exceptions.ClientError as e:
        logging.error(f"❌ Erro ao cadastrar rosto: {e.response['Error']['Message']}")
        return None


def reconhecer_aluno(nome_arquivo):
    """Reconhece um aluno a partir de uma imagem local."""
    if not rekognition_client:
        logger.error("❌ Cliente Rekognition não inicializado. Reconhecimento cancelado.")
        return None
    
    try:
        with open(nome_arquivo, "rb") as image_file:
            image_bytes = image_file.read()

        response = rekognition_client.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=80
        )

        if response.get('FaceMatches'):
            aluno_id = response['FaceMatches'][0]['Face']['ExternalImageId']
            logging.info(f"✅ Aluno reconhecido: {aluno_id}")
            return aluno_id
        
        else:
            logging.warning("❌ Rosto não reconhecido. Favor cadastrar.")
            return None

    except FileNotFoundError:
        logging.error(f"❌ Arquivo '{nome_arquivo}' não encontrado.")
        return None
    
    except botocore.exceptions.ClientError as e:
        logging.error(f"❌ Erro ao reconhecer aluno: {e.response['Error']['Message']}")
        return None


# Exemplo de execução protegida
if __name__ == "__main__":
    if rekognition_client: # Verifica se o cliente foi inicializado
        criar_colecao()
        
    else:
        logger.error("Cliente Rekognition não disponível para teste em rekognition_aws.py.")
    # Testes manuais aqui, se necessário
