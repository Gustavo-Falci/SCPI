
import boto3
import botocore.exceptions
import logging
from config import AWS_REGION, COLLECTION_ID  # Usa a configuração correta
from sistema_cadastrar_aluno import BUCKET_NAME

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Cliente Rekognition
rekognition = boto3.client('rekognition', region_name=AWS_REGION)


def criar_colecao():
    """Cria a coleção no Rekognition, se não existir."""
    try:
        rekognition.describe_collection(CollectionId=COLLECTION_ID)
        logging.info(f"A coleção '{COLLECTION_ID}' já existe.")
    except rekognition.exceptions.ResourceNotFoundException:
        try:
            response = rekognition.create_collection(CollectionId=COLLECTION_ID)
            logging.info(f"✅ Coleção '{COLLECTION_ID}' criada com sucesso!")
            return response
        except botocore.exceptions.ClientError as e:
            logging.error(f"❌ Erro ao criar a coleção: {e.response['Error']['Message']}")
            return None


def cadastrar_rosto(s3_path, aluno_id):
    """Cadastra o rosto de um aluno a partir de uma imagem no S3."""
    try:
        response = rekognition.index_faces(
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
    try:
        with open(nome_arquivo, "rb") as image_file:
            image_bytes = image_file.read()

        response = rekognition.search_faces_by_image(
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
    criar_colecao()
    # Testes manuais aqui, se necessário
