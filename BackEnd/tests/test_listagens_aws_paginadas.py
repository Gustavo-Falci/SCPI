"""Listagens AWS percorrem todas as páginas — auditoria sobre lista truncada mente."""
from unittest.mock import MagicMock, patch


def test_faces_concatena_duas_paginas():
    cliente = MagicMock()
    cliente.list_faces.side_effect = [
        {"Faces": [{"FaceId": "f1", "ExternalImageId": "ana", "ImageId": "i1"}],
         "NextToken": "tok1"},
        {"Faces": [{"FaceId": "f2", "ExternalImageId": "bruno", "ImageId": "i2"}]},
    ]
    with patch("infra.rekognition_aws.rekognition_client", cliente):
        from infra.rekognition_aws import listar_todas_faces
        faces, completo = listar_todas_faces()

    assert completo is True
    assert [f["face_id"] for f in faces] == ["f1", "f2"]
    assert faces[0]["external_image_id"] == "ana"
    # segunda chamada tem que mandar o token da primeira
    assert cliente.list_faces.call_args_list[1][1]["NextToken"] == "tok1"


def test_faces_primeira_chamada_sem_token():
    cliente = MagicMock()
    cliente.list_faces.return_value = {"Faces": []}
    with patch("infra.rekognition_aws.rekognition_client", cliente):
        from infra.rekognition_aws import listar_todas_faces
        listar_todas_faces()

    assert "NextToken" not in cliente.list_faces.call_args_list[0][1]


def test_faces_teto_de_paginas_marca_incompleto():
    """AWS devolvendo token para sempre não pode girar o servidor indefinidamente."""
    cliente = MagicMock()
    cliente.list_faces.return_value = {
        "Faces": [{"FaceId": "f", "ExternalImageId": "x", "ImageId": "i"}],
        "NextToken": "sempre",
    }
    with patch("infra.rekognition_aws.rekognition_client", cliente):
        from infra.rekognition_aws import listar_todas_faces, MAX_PAGINAS
        faces, completo = listar_todas_faces()

    assert completo is False
    assert cliente.list_faces.call_count == MAX_PAGINAS
    assert len(faces) == MAX_PAGINAS


def test_faces_sem_cliente_retorna_incompleto():
    with patch("infra.rekognition_aws.rekognition_client", None):
        from infra.rekognition_aws import listar_todas_faces
        assert listar_todas_faces() == ([], False)


def test_faces_erro_da_aws_retorna_incompleto():
    cliente = MagicMock()
    cliente.list_faces.side_effect = RuntimeError("AWS fora do ar")
    with patch("infra.rekognition_aws.rekognition_client", cliente):
        from infra.rekognition_aws import listar_todas_faces
        assert listar_todas_faces() == ([], False)


def test_s3_concatena_duas_paginas():
    cliente = MagicMock()
    cliente.list_objects_v2.side_effect = [
        {"Contents": [{"Key": "alunos/a.jpg", "Size": 10, "LastModified": None}],
         "NextContinuationToken": "tok1", "IsTruncated": True},
        {"Contents": [{"Key": "alunos/b.jpg", "Size": 20, "LastModified": None}],
         "IsTruncated": False},
    ]
    with patch("infra.s3_aws.s3_client", cliente):
        from infra.s3_aws import listar_todos_objetos_s3
        objetos, completo = listar_todos_objetos_s3()

    assert completo is True
    assert [o["key"] for o in objetos] == ["alunos/a.jpg", "alunos/b.jpg"]
    assert cliente.list_objects_v2.call_args_list[1][1]["ContinuationToken"] == "tok1"


def test_s3_ignora_pseudo_pastas():
    """Chave terminada em / é marcador de pasta, não arquivo de rosto."""
    cliente = MagicMock()
    cliente.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "alunos/", "Size": 0, "LastModified": None},
            {"Key": "alunos/a.jpg", "Size": 10, "LastModified": None},
        ],
        "IsTruncated": False,
    }
    with patch("infra.s3_aws.s3_client", cliente):
        from infra.s3_aws import listar_todos_objetos_s3
        objetos, _completo = listar_todos_objetos_s3()

    assert [o["key"] for o in objetos] == ["alunos/a.jpg"]


def test_s3_last_modified_vira_iso():
    from datetime import datetime

    cliente = MagicMock()
    cliente.list_objects_v2.return_value = {
        "Contents": [{"Key": "alunos/a.jpg", "Size": 10,
                      "LastModified": datetime(2026, 7, 1, 12, 0, 0)}],
        "IsTruncated": False,
    }
    with patch("infra.s3_aws.s3_client", cliente):
        from infra.s3_aws import listar_todos_objetos_s3
        objetos, _completo = listar_todos_objetos_s3()

    assert objetos[0]["last_modified"] == "2026-07-01T12:00:00"


def test_s3_teto_de_paginas_marca_incompleto():
    cliente = MagicMock()
    cliente.list_objects_v2.return_value = {
        "Contents": [{"Key": "alunos/a.jpg", "Size": 1, "LastModified": None}],
        "NextContinuationToken": "sempre", "IsTruncated": True,
    }
    with patch("infra.s3_aws.s3_client", cliente):
        from infra.s3_aws import listar_todos_objetos_s3, MAX_PAGINAS
        _objetos, completo = listar_todos_objetos_s3()

    assert completo is False
    assert cliente.list_objects_v2.call_count == MAX_PAGINAS


def test_s3_sem_cliente_retorna_incompleto():
    with patch("infra.s3_aws.s3_client", None):
        from infra.s3_aws import listar_todos_objetos_s3
        assert listar_todos_objetos_s3() == ([], False)
