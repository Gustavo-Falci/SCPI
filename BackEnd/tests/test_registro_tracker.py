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


def test_concluir_definitivo_sem_reivindicar_marca_resolvido():
    """Documenta por que o chamador precisa checar a geração da chamada.

    O tracker, sozinho, NÃO sabe que houve uma troca de chamada no meio do
    caminho: `concluir(..., definitivo=True)` sempre adiciona a
    `_resolvidos`, mesmo sem `reivindicar` anterior — é exatamente o caso de
    um POST de uma chamada A que já fechou, cuja resposta (409, definitivo)
    chega depois que `limpar()` já rodou para a chamada B. Se X também
    pertencer à chamada B, ele ficaria "resolvido" para sempre ali por engano.
    Quem protege contra isso não é esta classe: é `SistemaReconhecimento`, que
    só chama `concluir` se `self.chamada_id_atual` ainda for a chamada que
    originou aquele POST (ver `_registrar_presenca` em
    scripts/reconhecimento_tempo_real.py).
    """
    t = RegistroPresencaTracker()
    t.limpar()
    t.concluir("fantasma", definitivo=True)

    assert t.tratado("fantasma") is True
