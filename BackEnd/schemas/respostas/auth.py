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


class SessaoRenovada(RespostaBase):
    """Par de tokens novo devolvido pela rotação do refresh.

    Mesmos três campos do `Token` de `/auth/login`, e a duplicação é
    deliberada: `Token` é declarado por `response_model=` e VALIDA em runtime,
    então não pode ganhar `extra="forbid"` sem transformar documentação em
    erro de login. Este modelo só documenta.

    O refresh anterior é invalidado na troca (rotação): o `refresh_token` daqui
    é o único válido a partir da resposta. Quando a chamada veio por cookie, os
    mesmos tokens também voltam em `Set-Cookie` `HttpOnly` — o corpo é para o
    cliente mobile, que não tem cookie jar confiável.
    """

    access_token: str
    refresh_token: str
    token_type: str


class CodigoVerificado(RespostaBase):
    """Segundo passo da recuperação de senha: o código virou um `reset_token`.

    JWT de 15 minutos, de uso único (o `jti` é o id do código consumido), que
    só serve para `/auth/redefinir-senha`. É segredo de portador: não deve ser
    logado nem aparecer em URL. O código de 6 dígitos que o originou já está
    marcado como usado quando esta resposta sai.
    """

    reset_token: str
