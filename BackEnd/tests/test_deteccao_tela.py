"""Detector de tela por região emissiva — spec de campo 2026-08-16.

Rosto real não emite luz; rosto exibido está sempre dentro de uma tela acesa.
Medido na câmera da PORTA: 7/7 bursts de vídeo vetados (5/5 frames em todos) e
0/6 de rosto real — separação categórica, não margem.

A alternativa geométrica (traçar o retângulo do aparelho) foi medida e descartada:
Canny devolve curva aberta, celular ocluído pela mão dá 7-22 vértices no
approxPolyDP (nunca 4), e com o aparelho perto a moldura sai do quadro.
"""
import numpy as np

from scripts.deteccao_tela import regiao_emissiva


def _fundo(valor=40):
    return np.full((400, 400, 3), valor, dtype=np.uint8)


def test_rosto_dentro_de_area_acesa_e_detectado():
    img = _fundo()
    img[100:300, 150:250] = 240
    assert regiao_emissiva(img, (180, 170, 40, 50))[0] is True


def test_rosto_sem_area_acesa_nao_e_detectado():
    # Cena uniforme: nenhuma região se destaca. É o caso do rosto real.
    assert regiao_emissiva(_fundo(), (180, 170, 40, 50))[0] is False


def test_area_acesa_LONGE_do_rosto_nao_conta():
    # Lâmpada/janela num canto não pode vetar rosto do outro lado do quadro —
    # este é o falso positivo que tiraria presença de aluno legítimo.
    img = _fundo()
    img[10:80, 10:80] = 250
    assert regiao_emissiva(img, (300, 300, 40, 50))[0] is False


def test_area_acesa_menor_que_o_rosto_nao_conta():
    # Reflexo pontual sobre a pele não é aparelho: a tela é sempre MAIOR que o
    # rosto que ela exibe.
    img = _fundo()
    img[195:205, 195:205] = 250
    assert regiao_emissiva(img, (180, 180, 40, 40))[0] is False


def test_regiao_ocupando_o_quadro_inteiro_nao_conta():
    # Guarda de área: região que toma metade do quadro é a CENA, não aparelho.
    # Sem ela, cena de brilho uniforme veta todo rosto real.
    img = _fundo()
    img[0:400, 0:400] = 200
    assert regiao_emissiva(img, (180, 180, 40, 40))[0] is False


def test_devolve_razao_rosto_sobre_area():
    img = _fundo()
    img[100:300, 100:300] = 240          # 200x200 = 40000 px
    contem, razao = regiao_emissiva(img, (180, 180, 40, 40))   # rosto 1600 px
    assert contem is True
    assert 0.02 < razao < 0.08


def test_percentil_mais_alto_exige_mais_brilho():
    # Três níveis: em imagem de dois níveis o percentil não discrimina nada.
    img = _fundo()
    img[100:300, 150:250] = 200          # "tela" com o rosto dentro
    img[10:38, 10:38] = 255              # "lâmpada" no canto, longe do rosto
    box = (180, 170, 40, 50)
    assert regiao_emissiva(img, box, percentil=96)[0] is True
    assert regiao_emissiva(img, box, percentil=99.9)[0] is False


def test_bbox_degenerado_nao_quebra():
    assert regiao_emissiva(_fundo(), (10, 10, 0, 50))[0] is False
