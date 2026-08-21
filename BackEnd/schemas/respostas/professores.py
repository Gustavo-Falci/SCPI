from typing import Optional

from schemas.respostas.comum import RespostaBase


class AulaDeHoje(RespostaBase):
    """Aula prevista para o dia da semana atual. `horario` já vem formatado "HH:MM - HH:MM"."""

    id: str
    turma_id: str
    nome: str
    horario: str
    sala: Optional[str] = None


class EstatisticasDaChamada(RespostaBase):
    """Números da chamada mais recente do professor.

    Zerados com `disciplina="Nenhuma chamada recente"` quando ele nunca abriu
    uma — não é ausência de dado, é o estado inicial que a tela desenha.
    """

    total: int
    presentes: int
    parciais: int
    ausentes: int
    disciplina: str


class ChamadaAtivaDoProfessor(RespostaBase):
    """Chamada aberta agora. O bloco inteiro é `null` quando não há nenhuma."""

    chamada_id: int
    turma_id: Optional[str] = None
    turma_nome: Optional[str] = None


class DashboardDoProfessor(RespostaBase):
    nome: str
    estatisticas: EstatisticasDaChamada
    aulas_hoje: list[AulaDeHoje]
    chamada_ativa: Optional[ChamadaAtivaDoProfessor] = None
