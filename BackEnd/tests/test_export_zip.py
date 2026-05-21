"""Testes da montagem do ZIP multi-formato para export LGPD."""
import io
import json
import zipfile

from infra.export_zip import montar_zip_export


DADOS = {
    "titular": {
        "nome": "Ana",
        "email": "a@x.com",
        "ra": "1",
        "turno": "Manhã",
        "tipo_usuario": "aluno",
    },
    "biometria": {
        "registrada": False,
        "angulos_cadastrados": [],
        "consentimento_data": None,
        "revogado_em": None,
    },
    "presencas": [],
    "_schema_version": "1.0",
    "_gerado_em": "2026-05-21T14:00:00-03:00",
}
PDF_FAKE = b"%PDF-1.4 fake content"
FOTO_FAKE = b"\xff\xd8\xff\xe0fakejpeg"
MANIFESTO = {
    "sha256": "abc",
    "hmac_sha256": "def",
    "algoritmo": "HMAC-SHA256",
    "versao_schema": "1.0",
    "gerado_em": "2026-05-21T14:00:00-03:00",
}


def test_zip_contem_arquivos_obrigatorios():
    zip_bytes = montar_zip_export(DADOS, PDF_FAKE, MANIFESTO, foto_bytes=None)
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    nomes = set(z.namelist())
    assert "dados.json" in nomes
    assert "dados.pdf" in nomes
    assert "INTEGRIDADE.txt" in nomes
    assert "LEIA-ME.txt" in nomes
    assert "foto-perfil.jpg" not in nomes


def test_zip_inclui_foto_quando_fornecida():
    zip_bytes = montar_zip_export(DADOS, PDF_FAKE, MANIFESTO, foto_bytes=FOTO_FAKE)
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert "foto-perfil.jpg" in z.namelist()
    assert z.read("foto-perfil.jpg") == FOTO_FAKE


def test_zip_json_eh_parseavel_e_contem_dados():
    zip_bytes = montar_zip_export(DADOS, PDF_FAKE, MANIFESTO, foto_bytes=None)
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    dados_lidos = json.loads(z.read("dados.json"))
    assert dados_lidos["titular"]["nome"] == "Ana"


def test_zip_pdf_preservado():
    zip_bytes = montar_zip_export(DADOS, PDF_FAKE, MANIFESTO, foto_bytes=None)
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert z.read("dados.pdf") == PDF_FAKE


def test_zip_integridade_contem_hashes():
    zip_bytes = montar_zip_export(DADOS, PDF_FAKE, MANIFESTO, foto_bytes=None)
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    integ = z.read("INTEGRIDADE.txt").decode("utf-8")
    assert "abc" in integ
    assert "def" in integ
    assert "HMAC-SHA256" in integ


def test_zip_leia_me_menciona_lgpd():
    zip_bytes = montar_zip_export(DADOS, PDF_FAKE, MANIFESTO, foto_bytes=None)
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    leia_me = z.read("LEIA-ME.txt").decode("utf-8")
    assert "LGPD" in leia_me
    assert "Art. 18" in leia_me
