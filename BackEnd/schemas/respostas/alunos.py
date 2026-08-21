from typing import Literal, Optional

from schemas.respostas.comum import RespostaBase


class PoliticaVigenteNoConsentimento(RespostaBase):
    """Política em vigor AGORA — o front compara com `politica_versao` para
    decidir se pede novo aceite."""

    versao: str
    url: str


class EstadoDoConsentimento(RespostaBase):
    """Estado derivado do último evento da trilha append-only, não de coluna.

    `"nunca"` = nenhum evento registrado; `"ativo"` = último evento é aceite;
    `"revogado"` = último evento é revogação. `politica_versao` pode vir
    `"legado"` em aceite anterior ao versionamento, e `null` quando o estado é
    `"nunca"`. `registrado_em` é ISO 8601.
    """

    estado: Literal["nunca", "ativo", "revogado"]
    politica_versao: Optional[str] = None
    registrado_em: Optional[str] = None
    angulos_cadastrados: list[str]
    politica_vigente: PoliticaVigenteNoConsentimento
