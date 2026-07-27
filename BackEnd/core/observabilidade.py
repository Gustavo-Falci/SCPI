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
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger("scpi.observabilidade")

# Headers que carregam credencial. Comparação em minúsculas.
_HEADERS_SENSIVEIS = {"authorization", "cookie", "set-cookie", "x-service-token"}


def _limpar_evento(event, hint):
    """Hook before_send: tira credenciais e corpo de requisição do evento.

    Muta o evento in place (idioma do before_send) e o devolve; sem I/O,
    testável sem rede.
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
    # alguma integração futura o anexe por outro caminho. query_string e
    # cookies não são cobertos por send_default_pii=False — a integração ASGI
    # os popula incondicionalmente (sentry_sdk/integrations/_asgi_common.py) —
    # então removemos aqui também.
    request.pop("data", None)
    request.pop("cookies", None)
    request.pop("query_string", None)

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
        # sentry_sdk.init() sem integrations= liga a LoggingIntegration com os
        # defaults (DEFAULT_LEVEL=INFO, DEFAULT_EVENT_LEVEL=ERROR): todo
        # logger.error(...) do backend vira evento no Sentry e todo
        # logger.info/warning(...) vira breadcrumb anexado ao próximo evento —
        # com a mensagem já interpolada. O audit log (RA + IP do aluno em
        # chamadas.py) e o texto de erro do psycopg2 (e-mail em
        # "DETAIL: Key (email)=(...) already exists" em database.py) carregam
        # PII por esse caminho, e _limpar_evento não alcança nem
        # event["logentry"] nem event["breadcrumbs"] — before_send só vê o
        # evento já pronto. _audit_logger.propagate = False não protege: a
        # integração faz monkey-patch de logging.Logger.callHandlers, que roda
        # antes do propagate ser consultado. Desligamos a integração inteira;
        # com isso o Sentry só recebe exceções não tratadas de verdade.
        integrations=[LoggingIntegration(level=None, event_level=None)],
    )
    # set_tag grava na isolation scope (ContextVar) — threads fora da
    # propagação de contexto (loop.run_in_executor em services/agendador.py)
    # não a enxergam. A global scope é mesclada em todo evento, de qualquer
    # thread ou contexto.
    sentry_sdk.get_global_scope().set_tag("componente", componente)
    logger.info("Sentry ativo — componente %s.", componente)
    return True
