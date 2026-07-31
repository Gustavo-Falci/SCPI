"""Contabilidade de quem já foi tratado na chamada (sem rede, sem AWS).

Antes, o aluno entrava em `presentes_chamada` ANTES do POST: POST que falhava
nunca era tentado de novo e virava falta indevida silenciosa.
"""
from scripts.registro_tracker import RegistroPresencaTracker


def test_reivindicar_so_vale_para_o_primeiro():
    t = RegistroPresencaTracker()
    assert t.reivindicar("ana") is True
    assert t.reivindicar("ana") is False


def test_falha_transitoria_devolve_para_retry():
    t = RegistroPresencaTracker()
    t.reivindicar("ana")
    t.concluir("ana", definitivo=False)

    assert t.tratado("ana") is False
    assert t.reivindicar("ana") is True


def test_sucesso_nao_devolve():
    t = RegistroPresencaTracker()
    t.reivindicar("ana")
    t.concluir("ana", definitivo=True)

    assert t.tratado("ana") is True
    assert t.reivindicar("ana") is False


def test_tratado_cobre_quem_esta_em_voo():
    """Enquanto o POST está em andamento, não vale gastar SearchFaces de novo."""
    t = RegistroPresencaTracker()
    t.reivindicar("ana")

    assert t.tratado("ana") is True


def test_len_conta_apenas_resolvidos():
    t = RegistroPresencaTracker()
    t.reivindicar("ana")
    t.concluir("ana", definitivo=True)
    t.reivindicar("bruno")

    assert len(t) == 1


def test_limpar_zera_os_dois_conjuntos():
    t = RegistroPresencaTracker()
    t.reivindicar("ana")
    t.concluir("ana", definitivo=True)
    t.reivindicar("bruno")

    t.limpar()

    assert len(t) == 0
    assert t.tratado("ana") is False
    assert t.tratado("bruno") is False


def test_concluir_sem_reivindicar_nao_quebra():
    """Resposta atrasada depois de um limpar() por troca de chamada."""
    t = RegistroPresencaTracker()
    t.concluir("fantasma", definitivo=False)

    assert t.tratado("fantasma") is False
