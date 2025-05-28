from aws_clientes import rekognition_client
from config import COLLECTION_ID
import logging

# Configuração do Rekognition
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def listar_rostos():
    """Lista todos os rostos cadastrados na coleção do Rekognition."""

    if not rekognition_client:
        logger.error("Cliente Rekogntion não inicializado.")
        return

    response = rekognition_client.list_faces(CollectionId=COLLECTION_ID)
    faces = response.get("Faces", [])

    if not faces:
        print("✅ Nenhum rosto encontrado na coleção.")

    else:
        print("📌 Rostos cadastrados:")
        for face in faces:
            print(f"- FaceId: {face['FaceId']}, Nome: {face.get('ExternalImageId', 'Sem nome')}")


def excluir_todos_os_rostos():
    """Exclui todos os rostos cadastrados na coleção."""

    if not rekognition_client:
        logger.error("Cliente Rekognition não inicializado.")
        return

    response = rekognition_client.list_faces(CollectionId=COLLECTION_ID)
    faces = response.get("Faces", [])

    if not faces:
        print("✅ Nenhum rosto para excluir.")
        return

    face_ids = [face["FaceId"] for face in faces]  # Coleta todos os FaceIds
    rekognition_client.delete_faces(CollectionId=COLLECTION_ID, FaceIds=face_ids)  # Exclui os rostos

    print("✅ Todos os rostos foram removidos da coleção.")

if __name__ == "__main__": # Adiciona proteção para execução direta

    if rekognition_client:
        listar_rostos()
        excluir_todos_os_rostos() # Comente ou adicione uma confirmação
        
    else:
        logger.error("Cliente Rekognition não disponível para listar/excluir rostos.")

