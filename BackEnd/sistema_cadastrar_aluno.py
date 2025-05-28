from aws_clientes import s3_client
from rekognition_aws import indexar_rosto_da_imagem_s3
from config import BUCKET_NAME
import os
import logging
import botocore.exceptions


logger = logging.getLogger(__name__)


def upload_imagem_s3(imagem_path, aluno_id):
    """Faz upload da imagem para o S3."""
    if not s3_client:
        logger.error("❌ Cliente S3 não inicializado. Upload cancelado.")
        return None
    
    if not os.path.exists(imagem_path):
        logger.error(f"❌ Arquivo '{imagem_path}' não encontrado.")
        return None

    try:
        # Padronizar o nome do objeto S3 para usar o aluno_id formatado como ExternalImageId
        # Isso pode ajudar na consistência, mas é uma escolha de design.
        # Se aluno_id já é o formatado, ótimo. Senão, você pode querer formatá-lo aqui.
        # Por enquanto, vamos manter como está, assumindo que aluno_id é o nome desejado no S3 path.
        s3_path = f"alunos/{aluno_id}.jpg" # Este aluno_id é o input do usuário
        s3_client.upload_file(imagem_path, BUCKET_NAME, s3_path)
        logger.info(f"📤 Imagem enviada para: s3://{BUCKET_NAME}/{s3_path}")
        return s3_path
    
    except botocore.exceptions.ClientError as e:
        logger.error(f"❌ Erro ao enviar para o S3: {e.response['Error']['Message']}")
        return None


def cadastrar_aluno(imagem_path):
    """Cadastra aluno no S3 e Rekognition."""
    # O aluno_id aqui é o que o usuário digita.
    # Para Rekognition ExternalImageId, usamos um nome formatado.
    # A formatação é feita em cadastrar_reconhecer_Face_aluno.py.
    # Aqui, aluno_id é usado para o nome do arquivo S3 e como ExternalImageId.
    # Seria bom garantir que o aluno_id usado como ExternalImageId seja o formatado.
    # No entanto, este script `sistema_cadastrar_aluno.py` parece ser um script autônomo também.
    
    aluno_id_input = input("Digite o nome ou ID do aluno (será usado para ExternalImageId e nome do arquivo S3): ").strip()
    
    if not aluno_id_input:
        logger.error("Nome ou ID do aluno não pode ser vazio.")
        return None

    # Para consistência, vamos assumir que o ExternalImageId deve seguir o padrão de caracteres.
    # Se você tem uma função de formatação global (ex: em um utils.py), use-a aqui.
    # Por ora, faremos uma formatação simples se este script for usado diretamente.
    # import re
    # external_image_id = re.sub(r'[^a-zA-Z0-9_.\-:]', '', re.sub(r'\s+', '_', aluno_id_input))
    # Se este script NÃO for mais para ser executado diretamente, remova o input e a formatação daqui.
    # E receba o external_image_id formatado como parâmetro.

    s3_path_uploaded = upload_imagem_s3(imagem_path, aluno_id_input) # Usa o input para o nome do arquivo S3

    if s3_path_uploaded:
        # Chama a função unificada de rekognition_aws.py
        # Usa aluno_id_input como ExternalImageId, que é o comportamento original desta função.
        # O `DetectionAttributes` padrão da função unificada é "DEFAULT".
        logger.info(f"Chamando indexar_rosto_da_imagem_s3 para '{aluno_id_input}' (DetectionAttributes: DEFAULT).")
        return indexar_rosto_da_imagem_s3(s3_path_uploaded, aluno_id_input) # aluno_id_input usado como ExternalImageId
    return None


# Execução direta
if __name__ == "__main__":
    # Configuração de logging para execução direta
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(message)s")
    
    imagem_local = input("Informe o caminho da imagem local: ").strip()
    
    if not os.path.exists(imagem_local):
        logger.error(f"Caminho da imagem local '{imagem_local}' não encontrado.")

    else:
        resultado_cadastro = cadastrar_aluno(imagem_local) # Passa o caminho da imagem

        if resultado_cadastro:
            logger.info(f"Processo de cadastro para a imagem '{imagem_local}' concluído.")

        else:
            logger.error(f"Falha no processo de cadastro para a imagem '{imagem_local}'.")
