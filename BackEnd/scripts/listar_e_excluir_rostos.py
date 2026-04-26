import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from infra.aws_clientes import rekognition_client
from core.config import COLLECTION_ID
import logging

logger = logging.getLogger(__name__)

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

def excluir_rosto_por_id(external_image_id: str):
    """Exclui o(s) rosto(s) com ExternalImageId igual ao valor informado."""
    if not rekognition_client:
        logger.error("Cliente Rekognition não inicializado.")
        return

    response = rekognition_client.list_faces(CollectionId=COLLECTION_ID)
    faces = response.get("Faces", [])

    ids_para_excluir = [
        f["FaceId"] for f in faces if f.get("ExternalImageId") == external_image_id
    ]

    if not ids_para_excluir:
        print(f"Nenhum rosto encontrado com ExternalImageId='{external_image_id}'.")
        return

    rekognition_client.delete_faces(CollectionId=COLLECTION_ID, FaceIds=ids_para_excluir)
    print(f"✅ {len(ids_para_excluir)} rosto(s) com ExternalImageId='{external_image_id}' removido(s).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if rekognition_client:
        listar_rostos()
        excluir_rosto_por_id("Aluno_Teste")  # Exclui todos os rostos do Aluno_Teste
        # excluir_todos_os_rostos()             # Descomente para excluir TODOS

    else:
        logger.error("Cliente Rekognition não disponível para listar/excluir rostos.")

