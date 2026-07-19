"""Decisão de registro por burst de frames (liveness passivo).

Camada 1 — consenso X-de-Y: o mesmo aluno precisa dar match em
>= min_matches crops do burst (mata match espúrio de frame único). Incondicional.
Camada 2 — TEXTURA (gate de vida): modelo CNN local pontua cada crop; agrega-se
o MAX por aluno. Foto (papel/tela) satura em ~0.0 em todo frame; rosto vivo tem
ao menos um frame alto. Ver spec 2026-07-19 e scripts/anti_spoofing.py.
Camada 3 — pose-variance por magnitude hypot(std_yaw, std_pitch): ADVISORY.
Calculada e exposta para log/calibração, mas NÃO decide (textura já cobre o
ataque de foto, e a pose é ambígua: aluno parado ≈ foto). Paliativo de 2026-07-18.

Classe pura: sem AWS, sem câmera, sem env — testável isoladamente.
"""
import math
from dataclasses import dataclass
from enum import Enum
from statistics import pstdev


class Decisao(Enum):
    REGISTRAR = "registrar"
    PENDENTE = "pendente"
    DESCARTAR = "descartar"


@dataclass(frozen=True)
class ResultadoFrame:
    """Resultado de UM crop: identidade + pose (se coletada) + textura (se pontuada)."""
    external_id: str
    yaw: float | None = None
    pitch: float | None = None
    textura: float | None = None  # score de vida 0..1 do detector de textura


@dataclass(frozen=True)
class Avaliacao:
    """Decisão + métricas medidas (para log/calibração em campo)."""
    decisao: Decisao
    matches: int
    texture_max: float | None  # MAX dos scores de textura; None = nenhum pontuado
    std_yaw: float | None       # None = <2 amostras no eixo
    std_pitch: float | None
    magnitude: float | None     # hypot(std_yaw, std_pitch) — ADVISORY, não decide


class ConfirmadorBurst:
    def __init__(self, min_matches: int, pose_std_min: float, texture_min: float,
                 gate: str = "textura"):
        if min_matches < 1:
            raise ValueError("min_matches deve ser >= 1")
        if pose_std_min < 0:
            raise ValueError("pose_std_min deve ser >= 0")
        if not 0.0 <= texture_min <= 1.0:
            raise ValueError("texture_min deve estar em [0, 1]")
        if gate not in ("textura", "pose"):
            raise ValueError("gate deve ser 'textura' ou 'pose'")
        self.min_matches = min_matches
        self.pose_std_min = pose_std_min
        self.texture_min = texture_min
        # gate="textura": textura decide, pose advisory (default, modelo presente).
        # gate="pose": fallback paliativo (ENABLE_TEXTURE=off) — magnitude decide.
        self.gate = gate

    def avaliar(self, resultados: list[ResultadoFrame]) -> dict[str, Decisao]:
        """Contrato original: só as decisões."""
        return {eid: av.decisao for eid, av in self.avaliar_detalhado(resultados).items()}

    def avaliar_detalhado(self, resultados: list[ResultadoFrame]) -> dict[str, Avaliacao]:
        """Agrupa por external_id e decide pela TEXTURA; pose só como métrica."""
        por_id: dict[str, list[ResultadoFrame]] = {}
        for r in resultados:
            por_id.setdefault(r.external_id, []).append(r)

        avaliacoes: dict[str, Avaliacao] = {}
        for external_id, frames in por_id.items():
            texturas = [f.textura for f in frames if f.textura is not None]
            texture_max = max(texturas) if texturas else None

            yaws = [f.yaw for f in frames if f.yaw is not None]
            pitches = [f.pitch for f in frames if f.pitch is not None]
            std_yaw = pstdev(yaws) if len(yaws) >= 2 else None
            std_pitch = pstdev(pitches) if len(pitches) >= 2 else None
            magnitude = self._magnitude(std_yaw, std_pitch)

            vivo = (self._vivo_textura(texture_max) if self.gate == "textura"
                    else self._vivo_pose(magnitude))
            if len(frames) < self.min_matches:
                decisao = Decisao.DESCARTAR
            elif vivo:
                decisao = Decisao.REGISTRAR
            else:
                decisao = Decisao.PENDENTE

            avaliacoes[external_id] = Avaliacao(
                decisao=decisao, matches=len(frames), texture_max=texture_max,
                std_yaw=std_yaw, std_pitch=std_pitch, magnitude=magnitude,
            )
        return avaliacoes

    def _vivo_textura(self, texture_max: float | None) -> bool:
        # Fail-closed: sem score de textura em nenhum frame não se prova vida.
        if texture_max is None:
            return False
        return texture_max >= self.texture_min

    def _vivo_pose(self, magnitude: float | None) -> bool:
        # Gate paliativo (fallback ENABLE_TEXTURE=off). Fail-safe: sem pose => não vivo.
        if magnitude is None:
            return False
        return magnitude >= self.pose_std_min

    @staticmethod
    def _magnitude(std_yaw: float | None, std_pitch: float | None) -> float | None:
        # Métrica advisory (log). None = sem amostra em nenhum eixo.
        if std_yaw is None and std_pitch is None:
            return None
        return math.hypot(std_yaw or 0.0, std_pitch or 0.0)
