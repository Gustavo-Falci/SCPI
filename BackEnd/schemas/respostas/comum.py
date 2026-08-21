from pydantic import BaseModel, ConfigDict


class RespostaBase(BaseModel):
    """Base de todo modelo de saída: proíbe campo não documentado.

    `extra="forbid"` não afeta a API (estes modelos não filtram resposta em
    runtime); serve para a validação de teste falhar quando a rota passa a
    devolver um campo que ninguém documentou. Sem isso, o guarda de fidelidade
    só pegaria metade dos desalinhamentos.
    """

    model_config = ConfigDict(extra="forbid")


class MensagemResposta(RespostaBase):
    """Confirmação simples, sem corpo estruturado."""

    mensagem: str
