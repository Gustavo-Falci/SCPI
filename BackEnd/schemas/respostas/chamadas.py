from typing import Optional

from schemas.respostas.comum import RespostaBase


class ChamadaAbertaNaSala(RespostaBase):
    """`chamada_id` é `null` quando não há chamada aberta na sala do token agora
    — resposta normal, não erro."""

    chamada_id: Optional[int] = None


class PresencaDaCamera(RespostaBase):
    """`ja_registrado=true` é o caso idempotente: a presença já existia.

    Vem com 200 de propósito — o servidor tem o que a câmera queria gravar, e
    um 4xx faria a câmera insistir a cada burst.
    """

    mensagem: str
    ja_registrado: bool
