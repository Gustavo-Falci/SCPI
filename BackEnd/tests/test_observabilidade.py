"""Sentry com postura conservadora de PII.

O SCPI trata biometria e está em escopo LGPD. O SDK, por padrão, envia as
variáveis locais dos frames — o que carregaria senha em claro vinda do login(),
e-mail, RA e bytes de foto para um servidor de terceiro.
"""
from unittest.mock import patch

from sentry_sdk.integrations.logging import LoggingIntegration

from core.observabilidade import _limpar_evento, init_sentry


def test_limpar_evento_remove_headers_de_autenticacao():
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer abc.def.ghi",
                "Cookie": "scpi_access=xyz",
                # credencial do serviço de câmera (core/security.py:require_service_token,
                # enviada por scripts/reconhecimento_tempo_real.py)
                "X-Service-Token": "segredo-camera",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json",
            }
        }
    }

    limpo = _limpar_evento(event, {})

    headers = limpo["request"]["headers"]
    assert "Authorization" not in headers
    assert "Cookie" not in headers
    assert "X-Service-Token" not in headers
    # não sensíveis, úteis para diagnóstico
    assert headers["X-Requested-With"] == "XMLHttpRequest"
    assert headers["Content-Type"] == "application/json"


def test_limpar_evento_descarta_corpo_da_requisicao():
    event = {"request": {"data": {"senha": "hunter2", "email": "a@b.com"}}}

    limpo = _limpar_evento(event, {})

    assert "data" not in limpo["request"]


def test_limpar_evento_descarta_query_string_e_cookies():
    # sentry_sdk/integrations/_asgi_common.py popula query_string
    # incondicionalmente — não é coberto por send_default_pii=False.
    event = {
        "request": {
            "query_string": "ra=123456&email=aluno@escola.br",
            "cookies": {"scpi_access": "xyz"},
        }
    }

    limpo = _limpar_evento(event, {})

    assert "query_string" not in limpo["request"]
    assert "cookies" not in limpo["request"]


def test_limpar_evento_tolera_evento_sem_request():
    event = {"exception": {"values": []}}

    assert _limpar_evento(event, {}) == event


def test_init_sentry_sem_dsn_nao_inicializa():
    with patch.dict("os.environ", {"SENTRY_DSN": ""}, clear=False):
        with patch("core.observabilidade.sentry_sdk.init") as fake_init:
            assert init_sentry("api") is False
            fake_init.assert_not_called()


def test_init_sentry_com_dsn_desliga_pii():
    with patch.dict("os.environ", {"SENTRY_DSN": "https://k@o.ingest.sentry.io/1"}, clear=False):
        with patch("core.observabilidade.sentry_sdk.init") as fake_init:
            assert init_sentry("api") is True

    kwargs = fake_init.call_args.kwargs
    assert kwargs["send_default_pii"] is False
    assert kwargs["include_local_variables"] is False
    assert kwargs["max_request_body_size"] == "never"
    assert kwargs["traces_sample_rate"] == 0.0
    assert kwargs["before_send"] is _limpar_evento


def test_init_sentry_desliga_logging_integration():
    """Pin: sentry_sdk.init() sem integrations= liga LoggingIntegration por
    padrão (DEFAULT_LEVEL=INFO, DEFAULT_EVENT_LEVEL=ERROR), que transforma
    logger.error em evento e logger.info/warning em breadcrumb — ambos fora do
    alcance de _limpar_evento (before_send não vê logentry/breadcrumbs). Isso
    vazaria e-mail/RA/IP do audit log e dos erros do psycopg2. Precisamos que a
    integração passada esteja de fato desligada, não só presente.
    """
    with patch.dict("os.environ", {"SENTRY_DSN": "https://k@o.ingest.sentry.io/1"}, clear=False):
        with patch("core.observabilidade.sentry_sdk.init") as fake_init:
            init_sentry("api")

    kwargs = fake_init.call_args.kwargs
    integrations = kwargs["integrations"]
    logging_integrations = [i for i in integrations if isinstance(i, LoggingIntegration)]
    assert len(logging_integrations) == 1

    integracao = logging_integrations[0]
    # level=None e event_level=None fazem __init__ deixar estes atributos None
    # — é isso, e não algum "level" público, que de fato desarma a
    # integração (ver LoggingIntegration._handle_record).
    assert integracao._handler is None
    assert integracao._breadcrumb_handler is None


def test_init_sentry_seta_tag_na_global_scope():
    """sentry_sdk.set_tag grava na isolation scope (ContextVar) — threads fora
    da propagação de contexto (loop.run_in_executor em services/agendador.py)
    não a enxergam. A tag precisa estar na global scope, que é mesclada em
    todo evento independente de thread/contexto.
    """
    with patch.dict("os.environ", {"SENTRY_DSN": "https://k@o.ingest.sentry.io/1"}, clear=False):
        with patch("core.observabilidade.sentry_sdk.init"):
            with patch("core.observabilidade.sentry_sdk.get_global_scope") as fake_get_global:
                init_sentry("api")

    fake_get_global.return_value.set_tag.assert_called_once_with("componente", "api")
