"""Detector de tela por REGIÃO EMISSIVA — camada anti-replay (spec de campo 2026-08-16).

Fecha o buraco que o detector de textura (`anti_spoofing.py`) não fecha: replay
de vídeo em tela. A pergunta é geométrica, não de textura — **o rosto está
dentro de uma região que emite luz?** Rosto real não emite; rosto exibido está
sempre dentro de uma tela acesa.

Medido na câmera da PORTA em 2026-08-16, sobre bursts coletados no caminho real:
  video: 7/7 bursts vetados, com 5/5 frames marcados em TODOS
  real : 0/6 bursts vetados
Separação categórica, não margem. A textura, no mesmo dado, deixava passar 7/7
(scores 0.221-0.880 contra rosto real 0.997-0.9996 — folga de só 1.13x, que uma
iluminação ruim derruba: no apartamento o rosto real caiu a 0.002).

ALTERNATIVA MEDIDA E DESCARTADA — não repetir sem dado novo: traçar o retângulo
do aparelho por bordas. `findContours` sobre mapa do Canny não funciona (curvas
ABERTAS, área ~0); `approxPolyDP` nunca casa 4 vértices num celular ocluído pela
mão (dá 7-22); e com o aparelho perto a moldura sai do quadro, então não existe
retângulo na imagem. Ajuste "bem feito" mediu PIOR que a heurística crua.

LIMITES CONHECIDOS — isto é VETO, somado à textura, nunca gate único:
  - Falha aberto: não detectou não veta. Aparelho colado na câmera, ocupando o
    quadro, cai na guarda de área e escapa — é a textura que cobre esse caso.
  - O limiar é percentil DA CENA. Porta ensolarada, janela ou lâmpada no quadro
    podem mudar o comportamento; medido em uma iluminação só.
  - Atacante pode baixar o brilho da tela, ao custo de degradar o match na
    Rekognition.
"""
import cv2
import numpy as np


def regiao_emissiva(frame, bbox, percentil: float = 96.0) -> tuple[bool, float]:
    """(contém, razão) — o rosto está dentro de uma região que emite luz?

    `razão` = área do rosto / área da região. É o discriminante de escala entre
    tela de celular (rosto ocupa boa fração) e vão de porta iluminado (rosto é
    fração minúscula). Devolve (False, 0.0) quando nenhuma região serve.
    """
    x, y, w, h = bbox
    area_rosto = float(w * h)
    if area_rosto <= 0:
        return False, 0.0
    cx, cy = x + w / 2.0, y + h / 2.0

    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    limite = float(np.percentile(g, percentil))
    # `>=` e não `>`: quando a área acesa é maior que (100-percentil)% do quadro,
    # o próprio percentil cai DENTRO dela e `>` zeraria a máscara. O preço é a
    # cena uniforme virar máscara do quadro inteiro — barrado pela guarda de
    # área abaixo, não por limiar.
    mask = (g >= limite).astype(np.uint8) * 255
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    )
    contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Região que ocupa meio quadro é a CENA, não um aparelho. Sem esta guarda,
    # brilho uniforme veta rosto real — e falta silenciosa é o pior desfecho.
    area_max = frame.shape[0] * frame.shape[1] * 0.5

    melhor = (False, 0.0)
    for c in contornos:
        area = cv2.contourArea(c)
        if area <= area_rosto or area > area_max:
            continue
        if cv2.pointPolygonTest(c, (cx, cy), False) < 0:
            continue
        razao = area_rosto / area
        if not melhor[0] or razao > melhor[1]:
            melhor = (True, razao)
    return melhor
