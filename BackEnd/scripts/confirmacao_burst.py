"""Decisão de registro por burst de frames (liveness passivo).

Camada 1 — consenso X-de-Y: o mesmo aluno precisa dar match em
>= min_matches crops do burst (mata match espúrio de frame único).
Camada 2 — pose-variance: rosto 3D vivo varia yaw/pitch entre frames;
foto é plana (balançar muda posição/roll, nunca yaw/pitch do rosto impresso).

Classe pura: sem AWS, sem câmera, sem env — testável isoladamente.
"""
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

            if len(frames) < self.min_matches:
                decisao = Decisao.DESCARTAR
            elif self._vivo(std_yaw, std_pitch):
                decisao = Decisao.REGISTRAR
            else:
                decisao = Decisao.PENDENTE

            avaliacoes[external_id] = Avaliacao(
                decisao=decisao, matches=len(frames),
                std_yaw=std_yaw, std_pitch=std_pitch,
            )
        return avaliacoes

    def _vivo(self, std_yaw: float | None, std_pitch: float | None) -> bool:
        # Fail-safe incondicional: sem amostras suficientes (ambos None)
        # não se prova vida, independente do limiar configurado.
        candidatos = [s for s in (std_yaw, std_pitch) if s is not None]
        if not candidatos:
            return False
        return any(std >= self.pose_std_min for std in candidatos)
