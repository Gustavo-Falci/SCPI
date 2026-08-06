"""Piso de tamanho de rosto — spec 2026-08-06.

O MiniFASNetV2-SE é documentado para rosto de ~80px. Abaixo disso o crop
ampliado para 128x128 perde a alta frequência que separa pele de tela, e o
modelo devolve ~1.0 ("vivo") para qualquer coisa: medido em 2026-08-06, frames
de foto-em-tela com <40px deram mediana 0.9887 contra 0.0159 dos >=40px.
"""
import numpy as np
import pytest

from scripts.anti_spoofing import DetectorTextura, rosto_avaliavel


def test_rosto_acima_do_piso_e_avaliavel():
    assert rosto_avaliavel((10, 10, 120, 150), 80) is True


def test_rosto_abaixo_do_piso_nao_e_avaliavel():
    assert rosto_avaliavel((10, 10, 40, 50), 80) is False


def test_piso_exato_e_avaliavel():
    # Fixa o >=: 80 no piso de 80 passa.
    assert rosto_avaliavel((0, 0, 80, 80), 80) is True


def test_um_pixel_abaixo_do_piso_reprova():
    assert rosto_avaliavel((0, 0, 79, 200), 80) is False


def test_usa_o_lado_MENOR_nao_a_largura():
    # Rosto de perfil: alto e estreito. Passar por ser alto entregaria ao
    # modelo justamente o crop sem resolução horizontal.
    assert rosto_avaliavel((0, 0, 30, 300), 80) is False


def test_bbox_degenerado_reprova():
    assert rosto_avaliavel((0, 0, 0, 200), 80) is False
    assert rosto_avaliavel((0, 0, 200, 0), 80) is False


def test_piso_zero_aceita_qualquer_rosto():
    # Escape hatch operacional: piso 0 desliga o guard.
    assert rosto_avaliavel((0, 0, 1, 1), 0) is True


# ---- DetectorTextura: o piso vira "não sei", não "é fake" ----

class _NetFake:
    """Stub de cv2.dnn.Net: conta inferências e devolve logits fixos."""

    def __init__(self):
        self.inferencias = 0

    def setInput(self, blob):
        pass

    def forward(self):
        self.inferencias += 1
        # logits [live, fake] -> softmax dá p[0] ~= 0.982
        return np.array([[2.0, -2.0]], dtype=np.float32)


def _detector(face_min_px):
    """DetectorTextura sem carregar ONNX: __new__ pula o __init__."""
    d = DetectorTextura.__new__(DetectorTextura)
    d.net = _NetFake()
    d.liveness_min = 0.08
    d.face_min_px = face_min_px
    return d


def test_score_devolve_none_abaixo_do_piso():
    d = _detector(80)
    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    assert d.score(frame, (10, 10, 40, 40)) is None


def test_score_abaixo_do_piso_nao_roda_inferencia():
    # O guard vem ANTES de qualquer trabalho de cv2: nada de gastar CPU para
    # depois jogar o resultado fora.
    d = _detector(80)
    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    d.score(frame, (10, 10, 40, 40))
    assert d.net.inferencias == 0


def test_score_acima_do_piso_pontua_normalmente():
    d = _detector(80)
    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    s = d.score(frame, (10, 10, 120, 120))
    assert s == pytest.approx(0.9820, abs=1e-3)
    assert d.net.inferencias == 1


def test_vivo_foi_removida():
    # Tinha zero chamadores e semântica incompatível com None:
    # `None >= limiar` levanta TypeError para quem a usasse depois.
    assert not hasattr(DetectorTextura, "vivo")
