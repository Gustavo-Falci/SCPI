from typing import Optional

from schemas.respostas.comum import RespostaBase


class TurmaDoFiltro(RespostaBase):
    turma_id: str
    nome_disciplina: Optional[str] = None
    codigo_turma: Optional[str] = None


class ProfessorDoFiltro(RespostaBase):
    professor_id: str
    nome: Optional[str] = None


class OpcoesDeFiltro(RespostaBase):
    """Opções derivadas das chamadas FECHADAS existentes, não do cadastro.

    Assim o usuário não escolhe uma turma sem chamada nenhuma e recebe lista
    vazia sem entender. Na rota do professor o recorte já vem aplicado: só
    turmas dele aparecem. `professores` chega preenchida nas duas rotas — na do
    professor ela lista quem deu as chamadas das turmas dele.
    """

    turmas: list[TurmaDoFiltro]
    professores: list[ProfessorDoFiltro]
    turnos: list[str]
    semestres: list[str]
