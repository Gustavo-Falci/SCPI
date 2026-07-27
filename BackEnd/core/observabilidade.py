"""Telemetria de erros via Sentry, com postura conservadora de PII.

O SCPI trata biometria e está em escopo LGPD, e os eventos vão para o SaaS do
Sentry (EUA). Por isso desligamos tudo que carrega valor: PII automática,
variáveis locais dos frames e corpo de requisição. Chega tipo do erro, arquivo,
linha e stack — sem valores.

Uma denylist de nomes de campo foi descartada de propósito: é allowlist
invertida, sempre esquece um campo, e aqui o campo esquecido pode ser biometria.
"""
import logging
import os

import sentry_sdk

logger = logging.getLogger("scpi.observabilidade")

# Headers que carregam credencial. Comparação em minúsculas.
_HEADERS_SENSIVEIS = {"authorization", "cookie", "set-cookie", "x-camera-token"}


def _limpar_evento(event, hint):
    """Hook before_send: tira credenciais e corpo de requisição do evento.

    Função pura para ser testável sem rede.
    """
    request = event.get("request")
    if not request:
        return event

    headers = request.get("headers")
    if headers:
        request["headers"] = {
            nome: valor
            for nome, valor in headers.items()
            if nome.lower() not in _HEADERS_SENSIVEIS
        }

    # max_request_body_size='never' já evita o corpo; isto fecha a porta caso
    # alguma integração futura o anexe por outro caminho.
    request.pop("data", None)

    return event


def init_sentry(componente: str) -> bool:
    """Inicializa o Sentry para um ponto de entrada ('api', 'verificar_receipts').

    Devolve False quando SENTRY_DSN está ausente ou vazio — o caso normal em
    desenvolvimento. Não é fail-loud, ao contrário das migrations: observabilidade
    não é requisito de correção, e derrubar o boot por falta de telemetria troca
    um problema pequeno por um grande.
    """
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn:
        logger.info("Sentry desativado (SENTRY_DSN ausente) — componente %s.", componente)
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("ENVIRONMENT", "development"),
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
        before_send=_limpar_evento,
    )
    sentry_sdk.set_tag("componente", componente)
    logger.info("Sentry ativo — componente %s.", componente)
    return True
