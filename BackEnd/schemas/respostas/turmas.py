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


class AlunoDaTurma(RespostaBase):
    """Aluno matriculado, como a linha sai do SELECT.

    A chave do aluno aqui é `id`, e não `aluno_id` como na rota equivalente do
    Admin (`GET /admin/turmas/{turma_id}/alunos`, que renomeia o campo). São
    duas telas diferentes lendo a mesma consulta; o nome divergente é
    histórico e está documentado para o cliente não supor que é o mesmo corpo.
    """

    id: str
    nome: str
    email: str
    ra: str


class AlunosDaTurma(RespostaBase):
    """Turma sem matrícula devolve `alunos` vazio, não 404 — a lista vazia é a
    resposta correta para uma turma que existe e ainda não tem ninguém."""

    alunos: list[AlunoDaTurma]
