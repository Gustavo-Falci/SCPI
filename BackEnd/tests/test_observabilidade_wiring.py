"""Os dois pontos de entrada inicializam o Sentry.

Teste estrutural (lê o código-fonte) em vez de importar api.py, que executa
migrations e sobe o agendador no import.
"""
import pathlib

_BACKEND = pathlib.Path(__file__).resolve().parent.parent


def test_api_inicializa_sentry_antes_de_criar_o_app():
    fonte = (_BACKEND / "api.py").read_text(encoding="utf-8")

    assert "from core.observabilidade import init_sentry" in fonte
    # antes do FastAPI(...) para capturar falhas de startup
    assert fonte.index('init_sentry("api")') < fonte.index("app = FastAPI(")


def test_job_de_receipts_inicializa_sentry():
    fonte = (_BACKEND / "scripts" / "verificar_receipts.py").read_text(encoding="utf-8")

    assert "from core.observabilidade import init_sentry" in fonte
    assert 'init_sentry("verificar_receipts")' in fonte
