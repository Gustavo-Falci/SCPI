"""Os dois pontos de entrada inicializam o Sentry.

Teste estrutural (lê o código-fonte) em vez de importar api.py, que executa
migrations e sobe o agendador no import.
"""
import pathlib

_BACKEND = pathlib.Path(__file__).resolve().parent.parent


def test_api_inicializa_sentry_antes_de_criar_o_app():
    fonte = (_BACKEND / "api.py").read_text(encoding="utf-8")

    assert "from core.observabilidade import init_sentry" in fonte
    # Antes de qualquer outro import de core/infra (não só antes do
    # FastAPI(...)): RuntimeError de configuração ausente (SECRET_KEY,
    # SCPI_EXPORT_HMAC_KEY, DB_*) acontece na hora do import, e sem o Sentry já
    # inicializado essas falhas de deploy morrem silenciosas antes de existir
    # qualquer telemetria.
    assert fonte.index('init_sentry("api")') < fonte.index("from core.csrf import CSRFMiddleware")


def test_job_de_receipts_inicializa_sentry():
    fonte = (_BACKEND / "scripts" / "verificar_receipts.py").read_text(encoding="utf-8")

    assert "from core.observabilidade import init_sentry" in fonte
    assert 'init_sentry("verificar_receipts")' in fonte
