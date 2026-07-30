"""Trilha de consentimento no export LGPD Art. 18."""
from infra.export_pdf import _estilos, _secao_consentimentos, gerar_pdf_dados


def test_secao_lista_eventos():
    trilha = [
        {"evento": "aceite", "politica_versao": "1.0",
         "registrado_em": "2026-03-12T14:22:01", "ip": "203.0.113.7", "origem": "app"},
        {"evento": "revogacao", "politica_versao": "1.0",
         "registrado_em": "2026-05-01T09:00:00", "ip": "203.0.113.9", "origem": "app"},
    ]
    elementos = _secao_consentimentos(trilha, _estilos())
    assert elementos  # título + tabela


def test_secao_vazia_nao_quebra():
    elementos = _secao_consentimentos([], _estilos())
    assert elementos


def test_pdf_completo_com_trilha_gera_bytes():
    dados = {
        "titular": {"nome": "Ana Souza", "email": "ana@teste.local", "ra": "RA123"},
        "biometria": {"registrada": True, "angulos_cadastrados": ["frontal"],
                      "consentimento_data": "2026-03-12T14:22:01", "revogado_em": None},
        "presencas": [],
        "consentimentos": [
            {"evento": "aceite", "politica_versao": "1.0",
             "registrado_em": "2026-03-12T14:22:01", "ip": "203.0.113.7", "origem": "app"},
        ],
    }
    pdf = gerar_pdf_dados(dados)
    assert pdf[:4] == b"%PDF"


def test_pdf_sem_chave_consentimentos_nao_quebra():
    # Export gerado antes desta entrega não tem a chave.
    dados = {
        "titular": {"nome": "Ana Souza", "email": "ana@teste.local", "ra": "RA123"},
        "biometria": {"registrada": False},
        "presencas": [],
    }
    assert gerar_pdf_dados(dados)[:4] == b"%PDF"
