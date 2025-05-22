import boto3

# Configuração do Rekognition
rekognition = boto3.client("rekognition", region_name="us-east-1")  # Substitua pela sua região
COLECAO_ID = "sala_de_aula"

def listar_rostos():
    """Lista todos os rostos cadastrados na coleção do Rekognition."""
    response = rekognition.list_faces(CollectionId=COLECAO_ID)
    faces = response.get("Faces", [])

    if not faces:
        print("✅ Nenhum rosto encontrado na coleção.")
    else:
        print("📌 Rostos cadastrados:")
        for face in faces:
            print(f"- FaceId: {face['FaceId']}, Nome: {face.get('ExternalImageId', 'Sem nome')}")


def excluir_todos_os_rostos():
    """Exclui todos os rostos cadastrados na coleção."""
    response = rekognition.list_faces(CollectionId=COLECAO_ID)
    faces = response.get("Faces", [])

    if not faces:
        print("✅ Nenhum rosto para excluir.")
        return

    face_ids = [face["FaceId"] for face in faces]  # Coleta todos os FaceIds
    rekognition.delete_faces(CollectionId=COLECAO_ID, FaceIds=face_ids)  # Exclui os rostos

    print("✅ Todos os rostos foram removidos da coleção.")

# Testando as funções
listar_rostos()  # Lista os rostos antes de excluir
excluir_todos_os_rostos()  # Exclui todos os rostos

