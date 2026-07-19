"""Detector de textura (anti-spoofing por CNN local) — ver spec 2026-07-19.

Modelo facenox MiniFASNetV2-SE (best_model.onnx NÃO-quantizado, 1.9 MB, Apache-2.0)
rodando em cv2.dnn. Distingue rosto real de foto (papel/tela) pela textura,
independente de movimento — cobre o ataque que a pose-variance não resolve.

Preproc VALIDADO em ground-truth + câmera real a 2m (spec):
  crop scale 1.4 do bbox → blobFromImage(1/255, 128x128, swapRB=True) → softmax,
  classe 0 = live. Real 0.999 / 0.429–0.986; foto 0.000.
"""
import cv2
import numpy as np


class DetectorTextura:
    """Carrega o ONNX 1× e pontua crops. Fail-closed: erro de load levanta."""

    def __init__(self, model_path: str, liveness_min: float):
        try:
            self.net = cv2.dnn.readNetFromONNX(model_path)
        except cv2.error as e:
            raise RuntimeError(
                f"Falha ao carregar modelo de textura em {model_path}: {e}\n"
                "Use o best_model.onnx NÃO-quantizado (1.9 MB). O quantizado (626 KB) "
                "usa DynamicQuantizeLinear, não suportado por cv2.dnn."
            ) from e
        self.liveness_min = liveness_min

    def score(self, frame, bbox) -> float:
        """Liveness score 0..1 (1 = rosto vivo) para o crop do bbox no frame."""
        crop = _crop_scale(frame, bbox, 1.4)
        blob = cv2.dnn.blobFromImage(crop, 1 / 255.0, (128, 128), swapRB=True)
        self.net.setInput(blob)
        p = _softmax(self.net.forward().flatten())
        return float(p[0])  # classe 0 = live (facenox)

    def vivo(self, frame, bbox) -> bool:
        return self.score(frame, bbox) >= self.liveness_min


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
