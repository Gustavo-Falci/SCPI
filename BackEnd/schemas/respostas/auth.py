from typing import Optional

from schemas.respostas.comum import RespostaBase


class SessaoValida(RespostaBase):
    """Confirmação de sessão: o que o token afirma, sem consultar o banco.

    Os três campos são lidos direto das claims do access token — `usuario_id`
    vem de `sub`. Como não há consulta, um usuário excluído ainda recebe 200
    aqui até o token expirar; quem precisa do estado atual do cadastro usa as
    rotas do perfil.

    `email` é opcional porque sai de `.get()` na claim: token emitido sem ela
    devolve `null` em vez de quebrar a validação de sessão no boot do portal.
    """

    usuario_id: str
    email: Optional[str] = None
    role: str
