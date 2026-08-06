"""Agregação da validação Fase 0 — a conta que define o limiar de textura.

O gate de produção decide por MAX dos scores do burst (confirmacao_burst.
avaliar_detalhado). Logo a estatística que importa é max-por-burst, não
por frame: um único frame de vídeo acima do limiar já registra presença.
"""
import math

from scripts._validar_liveness import _max_por_burst, _meio_geometrico, _separacao


def test_max_por_burst_pega_o_maior_de_cada_burst():
    assert _max_por_burst([[0.01, 0.40, 0.02], [0.05, 0.06]]) == [0.40, 0.06]


def test_max_por_burst_descarta_burst_vazio():
    # Burst em que nenhum frame teve rosto detectado não vira amostra.
    assert _max_por_burst([[0.3], [], [0.1]]) == [0.3, 0.1]


def test_separacao_usa_pior_real_contra_melhor_fake():
    R, V, folga = _separacao([0.50, 0.20, 0.90], [0.01, 0.05, 0.02])
    assert R == 0.20
    assert V == 0.05
    assert folga == 4.0


def test_separacao_sem_amostra_devolve_none():
    assert _separacao([], [0.01]) == (None, None, None)
    assert _separacao([0.5], []) == (None, None, None)


def test_separacao_com_fake_zerado_nao_divide_por_zero():
    # Caso real: foto satura em 0.000 no frame raw (medição de 2026-07-19).
    R, V, folga = _separacao([0.30], [0.0, 0.0])
    assert R == 0.30
    assert V == 0.0
    assert folga == math.inf


def test_meio_geometrico():
    assert _meio_geometrico(0.32, 0.02) == 0.08
