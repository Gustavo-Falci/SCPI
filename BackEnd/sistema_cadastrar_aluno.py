from aws_clientes import s3_client, rekognition_client
from config import BUCKET_NAME, COLLECTION_ID
import os
import logging
import botocore.exceptions


logger = logging.getLogger(__name__)


def upload_imagem_s3(imagem_path, aluno_id):
    """Faz upload da imagem para o S3."""
    if not os.path.exists(imagem_path):
        logging.error(f"❌ Cliente S3 não inicializado. Upload cancelado.")
        return None

    try:
        s3_path = f"alunos/{aluno_id}.jpg"
        s3_client.upload_file(imagem_path, BUCKET_NAME, s3_path)
        logging.info(f"📤 Imagem enviada para: s3://{BUCKET_NAME}/{s3_path}")
        return s3_path
    except botocore.exceptions.ClientError as e:
        logging.error(f"❌ Erro ao enviar para o S3: {e.response['Error']['Message']}")
        return None


def cadastrar_rosto_rekognition(s3_path, aluno_id):
    """Cadastra o rosto no Rekognition a partir de uma imagem no S3."""
    try:
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={"S3Object": {"Bucket": BUCKET_NAME, "Name": s3_path}},
            ExternalImageId=aluno_id,
            DetectionAttributes=["DEFAULT"]
        )

        face_records = response.get("FaceRecords", [])
        if face_records:
            logging.info(f"✅ Rosto do aluno '{aluno_id}' registrado com sucesso!")
        else:
            logging.warning("⚠️ Nenhum rosto detectado ou erro ao registrar.")
        return response
    except botocore.exceptions.ClientError as e:
        logging.error(f"❌ Erro ao registrar rosto no Rekognition: {e.response['Error']['Message']}")
        return None


def cadastrar_aluno(imagem_path):
    """Cadastra aluno no S3 e Rekognition."""
    aluno_id = input("Digite o nome ou ID do aluno: ").strip()
    s3_path = upload_imagem_s3(imagem_path, aluno_id)
    if s3_path:
        return cadastrar_rosto_rekognition(s3_path, aluno_id)
    return None


# Execução direta
if __name__ == "__main__":
    imagem_local = input("Informe o caminho da imagem local: ").strip()
    cadastrar_aluno(imagem_local)
