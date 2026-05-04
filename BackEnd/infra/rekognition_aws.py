import logging

import botocore.exceptions
from infra.aws_clientes import rekognition_client
from core.config import BUCKET_NAME, COLLECTION_ID

# Configuração de logging
logger = logging.getLogger(__name__)



def indexar_rosto_da_imagem_s3(
    s3_path: str,
    external_image_id: str,
    detection_attributes: list[str] | str = "DEFAULT",
) -> dict | None:
    """
    Indexa um rosto de uma imagem no S3 para a coleção do Rekognition.

    Args:
        s3_path: O caminho para o objeto da imagem no S3 (ex: 'alunos/nome_aluno.jpg').
        external_image_id: O ID externo a ser associado ao rosto (ex: nome do aluno).
        detection_attributes: Atributos a serem detectados. Pode ser "DEFAULT" ou ["ALL"].

    Returns:
        A resposta da API do Rekognition ou None em caso de erro.
    """
    if not rekognition_client:
        logger.error("❌ Cliente Rekognition não inicializado. Indexação de rosto cancelada.")
        return None

    try:
        logger.info(
            f"Tentando indexar rosto para ExternalImageId: '{external_image_id}' da imagem S3: 's3://{BUCKET_NAME}/{s3_path}' com DetectionAttributes: '{detection_attributes}'"
        )
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={"S3Object": {"Bucket": BUCKET_NAME, "Name": s3_path}},
            ExternalImageId=external_image_id,
            DetectionAttributes=(
                [detection_attributes] if isinstance(detection_attributes, str) else detection_attributes
            ),  # Garante que seja uma lista
            MaxFaces=1,  # Indexar um rosto principal por imagem de cadastro
            QualityFilter="AUTO",  # Ou NONE, MEDIUM, HIGH - AUTO é um bom padrão
        )

        face_records = response.get("FaceRecords", [])
        unindexed_faces = response.get("UnindexedFaces", [])

        if face_records:
            face_id = face_records[0]["Face"]["FaceId"]
            logger.info(f"✅ Rosto indexado com sucesso! ExternalImageId: '{external_image_id}', FaceId: '{face_id}'.")

            if len(face_records) > 1:
                logger.warning(
                    f"⚠️ Múltiplos rostos foram detectados na imagem, mas apenas o de maior qualidade foi indexado devido a MaxFaces=1."
                )

        elif unindexed_faces:
            reason = unindexed_faces[0].get("Reasons", ["RAZÃO DESCONHECIDA"])[0]
            logger.warning(f"⚠️ Rosto não foi indexado para ExternalImageId: '{external_image_id}'. Razão: {reason}")

        else:
            # Isso pode ocorrer se a imagem não contiver rostos que atendam aos critérios de qualidade,
            # ou se MaxFaces=0 (o que não é o caso aqui).
            logger.warning(
                f"⚠️ Nenhum rosto foi indexado para ExternalImageId: '{external_image_id}' e nenhuma razão específica foi fornecida (pode ser qualidade baixa ou nenhum rosto detectado)."
            )

        return response

    except botocore.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(
            f"❌ Erro do cliente AWS ao indexar rosto para '{external_image_id}': {error_code} - {error_message}"
        )

        if "InvalidS3ObjectException" in str(e) or "Unable to get object metadata" in str(e):
            logger.error(
                f"Verifique se o objeto S3 's3://{BUCKET_NAME}/{s3_path}' existe e as permissões estão corretas."
            )
        return None

    except Exception as e:
        logger.error(
            f"❌ Erro inesperado ao indexar rosto para '{external_image_id}': {e}",
            exc_info=True,
        )
        return None


def deletar_rosto(face_id: str) -> bool:
    """
    Remove um rosto da coleção do Rekognition pelo FaceId.
    Usado como rollback quando o INSERT no banco falha após a indexação.
    """
    if not rekognition_client or not face_id:
        return False
    try:
        rekognition_client.delete_faces(CollectionId=COLLECTION_ID, FaceIds=[face_id])
        logger.info(f"🗑️ FaceId '{face_id}' removido da coleção '{COLLECTION_ID}'.")
        return True
    except Exception as e:
        logger.error(f"❌ Falha ao remover FaceId '{face_id}': {e}")
        return False


def reconhecer_aluno_por_bytes(image_bytes: bytes, face_match_threshold: int = 80) -> str | None:
    """
    Reconhece um aluno a partir dos bytes de uma imagem.

    Args:
        image_bytes: Os bytes da imagem a ser analisada.
        face_match_threshold: O limiar de confiança para considerar um rosto como correspondente.

    Returns:
        O ExternalImageId do aluno reconhecido ou None.
    """
    if not rekognition_client:
        logger.error("❌ Cliente Rekognition não inicializado. Reconhecimento cancelado.")
        return None

    if not image_bytes:
        logger.error("❌ Bytes da imagem não fornecidos para reconhecimento.")
        return None

    try:
        logger.info(
            f"Tentando reconhecer aluno a partir de imagem em memória ({len(image_bytes)} bytes) com threshold de {face_match_threshold}%."
        )
        response = rekognition_client.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={"Bytes": image_bytes},  # Usa os bytes diretamente
            MaxFaces=1,  # Procura o melhor match
            FaceMatchThreshold=face_match_threshold,
        )

        if response.get("FaceMatches"):
            match = response["FaceMatches"][0]
            aluno_id = match["Face"]["ExternalImageId"]
            confidence = match["Similarity"]
            logger.info(f"✅ Aluno reconhecido: {aluno_id} com confiança de {confidence:.2f}%")
            return aluno_id

        else:
            logger.warning("❌ Rosto não reconhecido na imagem fornecida (nenhuma correspondência acima do limiar).")
            return None

    except botocore.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]

        if error_code == "InvalidImageFormatException":
            logger.error(f"❌ Formato de imagem inválido ou imagem corrompida: {error_message}")

        elif error_code == "InvalidParameterException" and "no faces detected" in error_message.lower():
            logger.warning(f"⚠️ Nenhum rosto detectado na imagem pelo Rekognition para tentativa de reconhecimento.")

        elif error_code == "InvalidParameterException":
            logger.warning(f"⚠️ Parâmetro inválido ao chamar search_faces_by_image: {error_message}")

        else:
            logger.error(f"❌ Erro do cliente AWS ao reconhecer aluno: {error_code} - {error_message}")
        return None

    except Exception as e:
        logger.error(f"❌ Erro inesperado ao reconhecer aluno: {e}", exc_info=True)
        return None

