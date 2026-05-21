"""Testes do endpoint exportar_meus_dados (chamada direta, sem TestClient)."""
import io
import json
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import Response


def _dados_fake():
    return {
        "titular": {
            "nome": "Teste",
            "email": "t@x.com",
            "ra": "1",
            "turno": "Noite",
            "tipo_usuario": "aluno",
        },
        "biometria": {
            "registrada": False,
            "angulos_cadastrados": [],
            "consentimento_data": None,
            "revogado_em": None,
        },
        "presencas": [],
    }


def _user_aluno():
    return {"sub": "user-1", "role": "Aluno", "tipo_usuario": "aluno"}


def _stream_bytes(resp: Response) -> bytes:
    """Extrai bytes do corpo da resposta."""
    return resp.body


def test_endpoint_formato_json_mantem_retrocompat():
    from routers.alunos import exportar_meus_dados

    with patch("routers.alunos.buscar_dados_titular", return_value=_dados_fake()):
        resultado = exportar_meus_dados(
            usuario_id="user-1", formato="json", current_user=_user_aluno()
        )
    assert isinstance(resultado, dict)
    assert resultado["titular"]["nome"] == "Teste"
    assert resultado["_schema_version"] == "1.0"
    assert "_gerado_em" in resultado


def test_endpoint_formato_zip_retorna_streaming_response():
    from routers.alunos import exportar_meus_dados

    with patch("routers.alunos.buscar_dados_titular", return_value=_dados_fake()), \
         patch("routers.alunos.obter_path_foto_perfil_aluno", return_value=None), \
         patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": "a-1"}):
        resultado = exportar_meus_dados(
            usuario_id="user-1", formato="zip", current_user=_user_aluno()
        )
    assert isinstance(resultado, Response)
    assert resultado.media_type == "application/zip"
    assert "attachment" in resultado.headers["content-disposition"]
    assert ".zip" in resultado.headers["content-disposition"]

    body = _stream_bytes(resultado)
    z = zipfile.ZipFile(io.BytesIO(body))
    nomes = set(z.namelist())
    assert {"dados.json", "dados.pdf", "INTEGRIDADE.txt", "LEIA-ME.txt"}.issubset(nomes)


def test_endpoint_zip_eh_default():
    from routers.alunos import exportar_meus_dados

    with patch("routers.alunos.buscar_dados_titular", return_value=_dados_fake()), \
         patch("routers.alunos.obter_path_foto_perfil_aluno", return_value=None), \
         patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": "a-1"}):
        resultado = exportar_meus_dados(usuario_id="user-1", current_user=_user_aluno())
    assert isinstance(resultado, Response)


def test_endpoint_404_se_dados_nao_encontrados():
    from routers.alunos import exportar_meus_dados

    with patch("routers.alunos.buscar_dados_titular", return_value=None):
        with pytest.raises(HTTPException) as exc:
            exportar_meus_dados(usuario_id="user-1", current_user=_user_aluno())
    assert exc.value.status_code == 404


def test_endpoint_inclui_foto_quando_existe():
    from routers.alunos import exportar_meus_dados

    foto = b"\xff\xd8\xff\xe0fakejpeg"
    s3_mock = MagicMock()
    s3_mock.get_object.return_value = {"Body": MagicMock(read=lambda: foto)}
    with patch("routers.alunos.buscar_dados_titular", return_value=_dados_fake()), \
         patch("routers.alunos.obter_path_foto_perfil_aluno", return_value="alunos/x.jpg"), \
         patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": "a-1"}), \
         patch("routers.alunos.s3_client", s3_mock):
        resultado = exportar_meus_dados(
            usuario_id="user-1", formato="zip", current_user=_user_aluno()
        )
    body = _stream_bytes(resultado)
    z = zipfile.ZipFile(io.BytesIO(body))
    assert "foto-perfil.jpg" in z.namelist()
    assert z.read("foto-perfil.jpg") == foto


def test_endpoint_zip_falha_foto_continua_export():
    """Se S3 retornar erro, o ZIP é gerado sem foto e não quebra."""
    from routers.alunos import exportar_meus_dados

    s3_mock = MagicMock()
    s3_mock.get_object.side_effect = Exception("s3 unreachable")
    with patch("routers.alunos.buscar_dados_titular", return_value=_dados_fake()), \
         patch("routers.alunos.obter_path_foto_perfil_aluno", return_value="alunos/x.jpg"), \
         patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": "a-1"}), \
         patch("routers.alunos.s3_client", s3_mock):
        resultado = exportar_meus_dados(
            usuario_id="user-1", formato="zip", current_user=_user_aluno()
        )
    body = _stream_bytes(resultado)
    z = zipfile.ZipFile(io.BytesIO(body))
    assert "foto-perfil.jpg" not in z.namelist()
    assert "dados.json" in z.namelist()


def test_endpoint_zip_filename_contem_ra_e_timestamp():
    from routers.alunos import exportar_meus_dados

    with patch("routers.alunos.buscar_dados_titular", return_value=_dados_fake()), \
         patch("routers.alunos.obter_path_foto_perfil_aluno", return_value=None), \
         patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": "a-1"}):
        resultado = exportar_meus_dados(
            usuario_id="user-1", formato="zip", current_user=_user_aluno()
        )
    cd = resultado.headers["content-disposition"]
    assert "meus-dados-scpi-1-" in cd  # RA = "1" no fixture
    assert ".zip" in cd


def test_endpoint_json_contem_metadados_schema():
    from routers.alunos import exportar_meus_dados

    with patch("routers.alunos.buscar_dados_titular", return_value=_dados_fake()):
        resultado = exportar_meus_dados(
            usuario_id="user-1", formato="json", current_user=_user_aluno()
        )
    assert resultado["_schema_version"] == "1.0"
    assert "_gerado_em" in resultado


def test_zip_integridade_eh_verificavel():
    """SHA-256 dentro do INTEGRIDADE.txt deve bater com SHA-256 recomputado do dados.json."""
    import hashlib

    from routers.alunos import exportar_meus_dados

    with patch("routers.alunos.buscar_dados_titular", return_value=_dados_fake()), \
         patch("routers.alunos.obter_path_foto_perfil_aluno", return_value=None), \
         patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": "a-1"}):
        resultado = exportar_meus_dados(
            usuario_id="user-1", formato="zip", current_user=_user_aluno()
        )
    body = _stream_bytes(resultado)
    z = zipfile.ZipFile(io.BytesIO(body))

    dados_lidos = json.loads(z.read("dados.json"))
    payload_canonico = json.dumps(
        dados_lidos, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    sha_recomputado = hashlib.sha256(payload_canonico).hexdigest()

    integ_txt = z.read("INTEGRIDADE.txt").decode("utf-8")
    assert sha_recomputado in integ_txt
