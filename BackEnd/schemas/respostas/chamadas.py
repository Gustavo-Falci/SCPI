import datetime
from typing import Literal, Optional, Union

from schemas.respostas.comum import RespostaBase


class ChamadaAbertaNaSala(RespostaBase):
    """`chamada_id` é `null` quando não há chamada aberta na sala do token agora
    — resposta normal, não erro."""

    chamada_id: Optional[int] = None


class ChamadaAberta(RespostaBase):
    """A abertura é idempotente: já existindo chamada aberta para a turma, volta
    o `chamada_id` DELA em vez de criar duplicata. O cliente não distingue os
    dois casos pela resposta, e não precisa — o id é o mesmo que ele vai usar."""

    mensagem: str
    chamada_id: int


class PresencaDaCamera(RespostaBase):
    """`ja_registrado=true` é o caso idempotente: a presença já existia.

    Vem com 200 de propósito — o servidor tem o que a câmera queria gravar, e
    um 4xx faria a câmera insistir a cada burst.
    """

    mensagem: str
    ja_registrado: bool


class StatusComChamadaAberta(RespostaBase):
    """Turma com chamada aberta agora.

    As contagens são calculadas na hora, não persistidas: `ausentes` é
    `total_alunos - presentes` no instante da consulta, e muda a cada presença
    registrada pela câmera.
    """

    status: Literal["Aberta"]
    chamada_id: int
    horario_inicio: datetime.time
    total_alunos: int
    presentes: int
    ausentes: int


class StatusSemChamadaAberta(RespostaBase):
    """Turma sem chamada aberta: contadores zerados e nenhum id.

    Os zeros não são a contagem da turma — nada foi consultado. Não existe
    404 aqui: "não há chamada aberta" é resposta normal para a tela que
    decide entre abrir e retomar.
    """

    status: Literal["Fechada"]
    total_alunos: int
    presentes: int
    ausentes: int


# A rota devolve um dos dois formatos, e o `status` decide qual: sem chamada
# aberta não existem `chamada_id`/`horario_inicio` para devolver. Declarar um
# modelo só, com os dois campos opcionais, deixaria passar o caso em que a
# chamada existe mas o id sumiu da resposta.
StatusDaChamada = Union[StatusComChamadaAberta, StatusSemChamadaAberta]


class AlunoNaChamada(RespostaBase):
    """Aluno da turma na revisão da chamada.

    Todo aluno matriculado aparece, presente ou não: quem faltou vem com
    `aulas_presentes` vazio, e é essa linha que a tela usa para o ajuste
    manual. `aulas_presentes` traz o número de cada aula do slot (1, 2, ...).
    """

    id: str
    nome: str
    aulas_presentes: list[int]


class AlunosDaChamada(RespostaBase):
    """`total_aulas` vem da primeira linha da listagem; sem nenhum aluno
    matriculado, cai para o valor da própria chamada (e para 1 se nem isso
    existir), porque a tela precisa saber quantas colunas desenhar."""

    total_aulas: int
    alunos: list[AlunoNaChamada]
