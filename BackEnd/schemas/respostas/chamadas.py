from typing import Optional

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
