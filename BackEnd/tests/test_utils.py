import pytest
from core.utils import formatar_nome_para_external_id


def test_nome_sem_acento():
    assert formatar_nome_para_external_id("Joao Silva") == "Joao_Silva"


def test_nome_com_acento_agudo():
    assert formatar_nome_para_external_id("Luís") == "Luis"


def test_nome_com_acento_til():
    assert formatar_nome_para_external_id("João da Silva") == "Joao_da_Silva"


def test_nome_com_cedilha():
    assert formatar_nome_para_external_id("Françoise") == "Francoise"


def test_nome_com_multiplos_espacos():
    assert formatar_nome_para_external_id("  Ana   Paula  ") == "Ana_Paula"


def test_nome_vazio_apos_normalizacao():
    result = formatar_nome_para_external_id("!!!")
    assert result == ""


def test_nome_com_caracteres_permitidos():
    # . - : são permitidos pelo Rekognition
    assert formatar_nome_para_external_id("Silva-Jr.") == "Silva-Jr."


def test_mascaramento_external_id():
    aluno_id = "Joao_da_Silva"
    masked = aluno_id[:6] + "***" if len(aluno_id) > 6 else "***"
    assert masked == "Joao_d***"
    assert "Joao_da_Silva" not in masked  # nome completo não vaza


def test_mascaramento_external_id_curto():
    aluno_id = "Jo"
    masked = aluno_id[:6] + "***" if len(aluno_id) > 6 else "***"
    assert masked == "***"
