"""Sentry com postura conservadora de PII.

O SCPI trata biometria e está em escopo LGPD. O SDK, por padrão, envia as
variáveis locais dos frames — o que carregaria senha em claro vinda do login(),
e-mail, RA e bytes de foto para um servidor de terceiro.
"""
from unittest.mock import patch

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
