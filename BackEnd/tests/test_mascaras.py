"""Testes da máscara de documento pessoal usada nos PDFs de relatório."""
from core.mascaras import mascarar_documento


def test_cpf_valido_com_pontuacao_e_mascarado():
    assert mascarar_documento("529.982.247-25") == "***.982.247-**"


def test_cpf_valido_sem_pontuacao_e_mascarado():
    assert mascarar_documento("52998224725") == "***.982.247-**"


def test_sequencia_de_11_digitos_que_nao_e_cpf_passa_inteira():
    # DV inválido: não é CPF, é provavelmente um RA numérico longo.
    assert mascarar_documento("12345678900") == "12345678900"


def test_digitos_repetidos_nao_sao_tratados_como_cpf():
    assert mascarar_documento("11111111111") == "11111111111"


def test_ra_institucional_passa_inteiro():
    assert mascarar_documento("2023001234") == "2023001234"


def test_valor_vazio_vira_travessao():
    assert mascarar_documento("") == "—"
    assert mascarar_documento("   ") == "—"


def test_none_vira_travessao():
    assert mascarar_documento(None) == "—"


def test_travessao_do_banco_passa_inteiro():
    # COALESCE(al.ra, '—') já devolve travessão quando não há RA.
    assert mascarar_documento("—") == "—"
