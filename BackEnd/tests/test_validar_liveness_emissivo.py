"""Ferramenta de validação: piso de tamanho e agregação da camada emissiva.

O detector em si (`deteccao_tela.regiao_emissiva`) e o predicado de piso
(`anti_spoofing.rosto_avaliavel`) são de PRODUTO e têm testes próprios em
`test_deteccao_tela.py` e `test_anti_spoofing.py`. A ferramenta importa os dois
de propósito: medição e gate têm que usar a mesma função, senão o número medido
deixa de descrever o que roda na câmera.

O que se testa aqui é só o que a ferramenta acrescenta: aplicar o piso antes de
pontuar, e contar frames emissivos por burst.
"""
import cv2
import numpy as np

from scripts._validar_liveness import (
    _emissivo_do_burst, _max_por_burst, _scores_do_burst,
)


class _NetFake:
    """Stub de cv2.dnn.Net: conta inferências e devolve logits fixos."""

    def __init__(self):
        self.inferencias = 0

    def setInput(self, blob):
        pass

    def forward(self):
        self.inferencias += 1
        return np.array([[2.0, -2.0]], dtype=np.float32)


def _mk_frame(burst_dir, nome, box, pinta_tela=False):
    burst_dir.mkdir(parents=True, exist_ok=True)
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    if pinta_tela:
        img[100:300, 100:300] = 240        # "tela acesa" com o rosto dentro
    cv2.imwrite(str(burst_dir / f"{nome}.png"), img)
    (burst_dir / f"{nome}.txt").write_text("{} {} {} {}".format(*box))


# ---- Piso: espelha TEXTURE_FACE_MIN_PX do produto ----

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


# ---- Agregação da camada emissiva por burst ----

def test_emissivo_conta_frames_com_tela(tmp_path):
    _mk_frame(tmp_path, "frame_0", (180, 180, 40, 40), pinta_tela=True)
    _mk_frame(tmp_path, "frame_1", (180, 180, 40, 40), pinta_tela=True)
    _mk_frame(tmp_path, "frame_2", (180, 180, 40, 40), pinta_tela=False)
    assert _emissivo_do_burst(tmp_path) == (2, 3)


def test_emissivo_burst_limpo_conta_zero(tmp_path):
    _mk_frame(tmp_path, "frame_0", (180, 180, 40, 40))
    _mk_frame(tmp_path, "frame_1", (180, 180, 40, 40))
    assert _emissivo_do_burst(tmp_path) == (0, 2)


def test_emissivo_burst_vazio(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    assert _emissivo_do_burst(tmp_path) == (0, 0)
