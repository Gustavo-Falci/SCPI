from typing import Literal

from schemas.respostas.comum import RespostaBase


class ApiNoAr(RespostaBase):
    """Resposta da raiz: só confirma que a API responde."""

    mensagem: str


class PoliticaPrivacidadeVigente(RespostaBase):
    """Versão da política que o app precisa mostrar antes do aceite."""

    versao: str
    data_vigencia: str
    url: str


class SaudeDaApi(RespostaBase):
    """Healthcheck. `status`/`database` são "ok" no 200 e "degraded"/"error" no 503."""

    status: Literal["ok", "degraded"]
    database: Literal["ok", "error"]
