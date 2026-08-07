"""Detector de textura (anti-spoofing por CNN local) — specs 2026-07-19 e 2026-08-06.

Modelo facenox MiniFASNetV2-SE (best_model.onnx NÃO-quantizado, 1.9 MB,
Apache-2.0) rodando em cv2.dnn.

FAIXA DE VALIDADE (spec 2026-08-06): rosto de ~80px ou mais. Dentro dela, o
preproc validado é crop scale 1.4 do bbox → blobFromImage(1/255, 128x128,
swapRB=True) → softmax, classe 0 = live.

FORA dela o modelo NÃO separa nada: com rosto <40px, foto em tela deu mediana
0.9887 ("vivo"). Por isso `score()` devolve None abaixo de `face_min_px`, em
vez de um número que parece resposta. Ver `rosto_avaliavel`.

ATENÇÃO — o que este módulo NÃO cobre: em 2026-08-06 um celular exibindo foto
de aluno registrou presença em produção (texture_max=0.854 contra limiar 0.08).
O fallback de pose aprovou o mesmo ataque (magnitude=2.98 contra 2.0), então
ENABLE_TEXTURE=0 não é mitigação. A camada anti-replay (bezel/moiré) ainda não
existe; tela grande colada na câmera segue sendo risco aberto.
"""
import cv2
import numpy as np


def rosto_avaliavel(bbox, minimo: int) -> bool:
    """O modelo tem resolução para opinar sobre este bbox?

    MiniFASNetV2-SE é documentado para rosto de ~80px. Abaixo disso o crop
    ampliado para 128x128 perde a alta frequência (moiré, grade de tela, grão)
    que separa pele de tela, e o modelo passa a devolver ~1.0 para QUALQUER
    coisa. Medição de 2026-08-06: frames de foto-em-tela com <40px deram
    mediana 0.9887; os mesmos com >=40px, 0.0159.

    Compara o LADO MENOR: rosto de perfil é alto e estreito, e aprovar por ser
    alto entregaria ao modelo justamente o crop sem resolução.
    """
    _x, _y, w, h = bbox
    return min(w, h) >= minimo


class DetectorTextura:
    """Carrega o ONNX 1× e pontua crops. Fail-closed: erro de load levanta."""

    def __init__(self, model_path: str, liveness_min: float, face_min_px: int):
        try:
            self.net = cv2.dnn.readNetFromONNX(model_path)
        except cv2.error as e:
            raise RuntimeError(
                f"Falha ao carregar modelo de textura em {model_path}: {e}\n"
                "Use o best_model.onnx NÃO-quantizado (1.9 MB). O quantizado (626 KB) "
                "usa DynamicQuantizeLinear, não suportado por cv2.dnn."
            ) from e
        self.liveness_min = liveness_min
        self.face_min_px = face_min_px

    def score(self, frame, bbox) -> float | None:
        """Liveness score 0..1 (1 = rosto vivo), ou None se o rosto for pequeno
        demais para o modelo opinar.

        None NÃO significa "fake": significa ausência de prova de vida.
        ConfirmadorBurst já descarta texturas None e cai em PENDENTE quando não
        sobra nenhuma — fail-closed, sem estado novo.
        """
        if not rosto_avaliavel(bbox, self.face_min_px):
            return None
        crop = _crop_scale(frame, bbox, 1.4)
        blob = cv2.dnn.blobFromImage(crop, 1 / 255.0, (128, 128), swapRB=True)
        self.net.setInput(blob)
        p = _softmax(self.net.forward().flatten())
        return float(p[0])  # classe 0 = live (facenox)


def _softmax(v):
    e = np.exp(v - np.max(v))
    return e / e.sum()


def _crop_scale(frame, bbox, scale):
    """Recorte quadrado centrado no bbox, expandido por `scale`, com clamp.
    Idêntico ao usado na validação (scripts/_validar_liveness.py)."""
    x, y, w, h = bbox
    cx, cy = x + w / 2.0, y + h / 2.0
    lado = max(w, h) * scale
    x1 = int(max(0, cx - lado / 2)); y1 = int(max(0, cy - lado / 2))
    x2 = int(min(frame.shape[1], cx + lado / 2)); y2 = int(min(frame.shape[0], cy + lado / 2))
    return cv2.resize(frame[y1:y2, x1:x2], (128, 128))
