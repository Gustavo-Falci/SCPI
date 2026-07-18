"""Decisão de registro por burst de frames (liveness passivo).

Camada 1 — consenso X-de-Y: o mesmo aluno precisa dar match em
>= min_matches crops do burst (mata match espúrio de frame único).
Camada 2 — pose-variance por MAGNITUDE COMBINADA: rosto 3D vivo varia yaw
E pitch juntos (micro-tremor de cabeça real). Foto inclinada tomba num eixo
só — a hipotenusa hypot(std_yaw, std_pitch) acumula os dois eixos, então
variação concentrada num único eixo (assinatura de foto) fica baixa e não
cruza o limiar. Ver conversa 2026-07-18 (paliativo até o modelo de textura).

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
    """Resultado de UM crop enviado à AWS: identidade + pose (se coletada)."""
    external_id: str
    yaw: float | None = None
    pitch: float | None = None


@dataclass(frozen=True)
class Avaliacao:
    """Decisão + métricas medidas (para log/calibração em campo)."""
    decisao: Decisao
    matches: int
    std_yaw: float | None   # None = <2 amostras no eixo
    std_pitch: float | None
    magnitude: float | None  # hypot(std_yaw, std_pitch); None = sem pose alguma


class ConfirmadorBurst:
    def __init__(self, min_matches: int, pose_std_min: float):
        if min_matches < 1:
            raise ValueError("min_matches deve ser >= 1")
        if pose_std_min < 0:
            raise ValueError("pose_std_min deve ser >= 0")
        self.min_matches = min_matches
        self.pose_std_min = pose_std_min

    def avaliar(self, resultados: list[ResultadoFrame]) -> dict[str, Decisao]:
        """Contrato original: só as decisões."""
        return {eid: av.decisao for eid, av in self.avaliar_detalhado(resultados).items()}

    def avaliar_detalhado(self, resultados: list[ResultadoFrame]) -> dict[str, Avaliacao]:
        """Agrupa por external_id e decide, expondo matches e desvios medidos."""
        por_id: dict[str, list[ResultadoFrame]] = {}
        for r in resultados:
            por_id.setdefault(r.external_id, []).append(r)

        avaliacoes: dict[str, Avaliacao] = {}
        for external_id, frames in por_id.items():
            yaws = [f.yaw for f in frames if f.yaw is not None]
            pitches = [f.pitch for f in frames if f.pitch is not None]
            std_yaw = pstdev(yaws) if len(yaws) >= 2 else None
            std_pitch = pstdev(pitches) if len(pitches) >= 2 else None
            magnitude = self._magnitude(std_yaw, std_pitch)

            if len(frames) < self.min_matches:
                decisao = Decisao.DESCARTAR
            elif self._vivo(magnitude):
                decisao = Decisao.REGISTRAR
            else:
                decisao = Decisao.PENDENTE

            avaliacoes[external_id] = Avaliacao(
                decisao=decisao, matches=len(frames),
                std_yaw=std_yaw, std_pitch=std_pitch, magnitude=magnitude,
            )
        return avaliacoes

    @staticmethod
    def _magnitude(std_yaw: float | None, std_pitch: float | None) -> float | None:
        # Sem amostra em nenhum eixo => sem medida de vida (None, não 0.0):
        # 0.0 seria "medido e rígido"; None é "não medido" (fail-safe distinto).
        if std_yaw is None and std_pitch is None:
            return None
        return math.hypot(std_yaw or 0.0, std_pitch or 0.0)

    def _vivo(self, magnitude: float | None) -> bool:
        # Fail-safe incondicional: sem magnitude (nenhuma pose coletada)
        # não se prova vida, independente do limiar configurado.
        if magnitude is None:
            return False
        return magnitude >= self.pose_std_min
