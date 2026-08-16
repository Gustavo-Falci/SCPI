"""Detector de região emissiva — candidato a camada B (medição de 2026-08-06).

Ideia do Gustavo: achar o aparelho e descartar todo rosto DENTRO dele. Ajustar
o retângulo por bordas falhou (Canny dá curva aberta; celular ocluído pela mão
dá 7-22 vértices, nunca 4). O que separou foi luminância: rosto real nunca cai
dentro de uma região que emite luz; rosto exibido está sempre dentro de uma
tela acesa.

Sobre as 17 amostras: 0/5 falso positivo em `real`, 4/6 de `tela` e 5/6 de
`video` vetados. NÃO é gate de produto — é instrumento de medição, para a
coleta na porta responder se o sinal sobrevive com fundo e luz reais.
"""
import cv2
import numpy as np

from scripts._validar_liveness import (
    _max_por_burst, _regiao_emissiva, _rosto_avaliavel, _scores_do_burst,
)


def _fundo(valor=40):
    return np.full((400, 400, 3), valor, dtype=np.uint8)


def test_rosto_dentro_de_area_acesa_e_detectado():
    # Tela acesa (retângulo claro) com o rosto no meio dela.
    img = _fundo()
    img[100:300, 150:250] = 240
    assert _regiao_emissiva(img, (180, 170, 40, 50))[0] is True


def test_rosto_sem_area_acesa_nao_e_detectado():
    # Cena uniforme: nenhuma região se destaca. É o caso do rosto real.
    assert _regiao_emissiva(_fundo(), (180, 170, 40, 50))[0] is False


def test_area_acesa_LONGE_do_rosto_nao_conta():
    # Lâmpada/janela num canto não pode vetar um rosto do outro lado — este é
    # o falso positivo que mataria aluno legítimo numa porta ensolarada.
    img = _fundo()
    img[10:80, 10:80] = 250          # brilho no canto superior esquerdo
    assert _regiao_emissiva(img, (300, 300, 40, 50))[0] is False


def test_area_acesa_menor_que_o_rosto_nao_conta():
    # Reflexo pontual sobre o rosto não é aparelho: a tela tem que ser MAIOR
    # que o rosto que ela exibe.
    img = _fundo()
    img[195:205, 195:205] = 250
    assert _regiao_emissiva(img, (180, 180, 40, 40))[0] is False


def test_devolve_razao_rosto_sobre_area():
    # A razão é o discriminante de escala entre tela de celular (rosto ocupa
    # boa fração) e vão de porta iluminado (rosto é fração minúscula).
    img = _fundo()
    img[100:300, 100:300] = 240      # 200x200 = 40000 px
    contem, razao = _regiao_emissiva(img, (180, 180, 40, 40))   # rosto 1600 px
    assert contem is True
    assert 0.02 < razao < 0.08


def test_percentil_mais_alto_exige_mais_brilho():
    # Controle de sensibilidade, com TRÊS níveis — em imagem de dois níveis o
    # percentil não discrimina nada (qualquer corte na faixa clara pega o
    # retângulo inteiro), que é o caso da porta ensolarada onde o sinal pode
    # degradar. Aqui: fundo escuro, tela média com o rosto, e um ponto muito
    # mais claro (lâmpada) longe do rosto.
    img = _fundo()
    img[100:300, 150:250] = 200      # "tela" com o rosto dentro
    img[10:38, 10:38] = 255          # "lâmpada" no canto, longe do rosto
    box = (180, 170, 40, 50)

    # percentil 96 corta na faixa da tela => acusa
    assert _regiao_emissiva(img, box, percentil=96)[0] is True
    # percentil 99.9 corta só na lâmpada, que não contém o rosto => não acusa
    assert _regiao_emissiva(img, box, percentil=99.9)[0] is False


# ---- Piso de tamanho: espelha TEXTURE_FACE_MIN_PX do produto ----

class _NetFake:
    """Stub de cv2.dnn.Net: conta inferências e devolve logits fixos."""

    def __init__(self):
        self.inferencias = 0

    def setInput(self, blob):
        pass

    def forward(self):
        self.inferencias += 1
        return np.array([[2.0, -2.0]], dtype=np.float32)


def _mk_frame(burst_dir, nome, box):
    burst_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(burst_dir / f"{nome}.png"),
                np.zeros((400, 400, 3), dtype=np.uint8))
    (burst_dir / f"{nome}.txt").write_text("{} {} {} {}".format(*box))


def test_piso_usa_o_lado_menor_e_aceita_o_valor_exato():
    # Mesma semântica de anti_spoofing.rosto_avaliavel (fix/piso-tamanho-rosto-
    # textura). Se estes dois divergirem, o número medido deixa de descrever o
    # gate — é o motivo de a duplicata ter data de validade.
    assert _rosto_avaliavel((0, 0, 80, 80), 80) is True
    assert _rosto_avaliavel((0, 0, 79, 200), 80) is False
    assert _rosto_avaliavel((0, 0, 30, 300), 80) is False
    assert _rosto_avaliavel((0, 0, 1, 1), 0) is True


def test_scores_do_burst_sem_piso_pontua_todos(tmp_path):
    _mk_frame(tmp_path, "frame_0", (10, 10, 40, 40))
    _mk_frame(tmp_path, "frame_1", (10, 10, 120, 120))
    net = _NetFake()
    assert len(_scores_do_burst(net, tmp_path, "facenox")) == 2
    assert net.inferencias == 2


def test_scores_do_burst_com_piso_descarta_rosto_pequeno(tmp_path):
    _mk_frame(tmp_path, "frame_0", (10, 10, 40, 40))    # abaixo
    _mk_frame(tmp_path, "frame_1", (10, 10, 120, 120))  # acima
    net = _NetFake()
    assert len(_scores_do_burst(net, tmp_path, "facenox", piso=80)) == 1
    assert net.inferencias == 1


def test_burst_todo_abaixo_do_piso_vira_vazio_nao_zero(tmp_path):
    # Ausência de amostra, não "fake perfeito". Zerar inflaria a separação —
    # é a armadilha 1 da spec de 2026-08-05 entrando por outra porta.
    _mk_frame(tmp_path, "frame_0", (10, 10, 40, 40))
    _mk_frame(tmp_path, "frame_1", (10, 10, 30, 30))
    scores = _scores_do_burst(_NetFake(), tmp_path, "facenox", piso=80)
    assert scores == []
    assert _max_por_burst([scores]) == []
