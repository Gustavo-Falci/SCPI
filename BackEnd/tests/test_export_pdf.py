"""Testes do gerador de PDF do export LGPD."""
from infra.export_pdf import gerar_pdf_dados


DADOS_FIXTURE = {
    "titular": {
        "nome": "João da Silva",
        "email": "joao@exemplo.com",
        "ra": "12345",
        "turno": "Noite",
        "tipo_usuario": "aluno",
    },
    "biometria": {
        "registrada": True,
        "angulos_cadastrados": ["frente", "esquerda", "direita", "cima"],
        "consentimento_data": "2026-03-10T14:00:00-03:00",
        "revogado_em": None,
    },
    "presencas": [
        {"turma": "Matemática", "data": "2026-05-20", "hora_registro": "08:15:00"},
        {"turma": "Português", "data": "2026-05-19", "hora_registro": "10:05:00"},
    ],
    "_schema_version": "1.0",
    "_gerado_em": "2026-05-21T14:30:00-03:00",
}


def test_pdf_retorna_bytes_validos():
    pdf = gerar_pdf_dados(DADOS_FIXTURE)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_pdf_sem_presencas():
    dados = {**DADOS_FIXTURE, "presencas": []}
    pdf = gerar_pdf_dados(dados)
    assert pdf.startswith(b"%PDF-")


def test_pdf_sem_biometria():
    dados = {
        **DADOS_FIXTURE,
        "biometria": {
            "registrada": False,
            "angulos_cadastrados": [],
            "consentimento_data": None,
            "revogado_em": None,
        },
    }
    pdf = gerar_pdf_dados(dados)
    assert pdf.startswith(b"%PDF-")
