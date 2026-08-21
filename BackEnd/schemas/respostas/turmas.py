from typing import Optional

from schemas.respostas.comum import RespostaBase


class TurmaDoProfessor(RespostaBase):
    """Turma com o estado que decide o botão da tela do professor.

    `pode_iniciar` é calculado do horário atual (America/Sao_Paulo), não vem
    do banco. `proximo_horario` é texto pronto para exibição — "Hoje: 19:00 -
    20:40", "Quarta: 19:00" ou "Sem horário definido".
    """

    turma_id: str
    nome_disciplina: str
    codigo_turma: str
    pode_iniciar: bool
    proximo_horario: str
    chamada_aberta: bool
    chamada_id: Optional[int] = None


class TurmasDoProfessor(RespostaBase):
    turmas: list[TurmaDoProfessor]
