"""`agora_utc()` substitui `datetime.utcnow()` sem mudar o tipo devolvido.

O ponto delicado: `utcnow()` devolve datetime NAIVE, e as colunas que guardam
esses valores (`RefreshTokens.expires_at`, `password_reset_tokens.expires_at`)
são `TIMESTAMP` sem time zone — psycopg2 as lê de volta naive. Trocar por
`datetime.now(timezone.utc)`, que é AWARE, faria as comparações destes dois
caminhos levantarem `TypeError: can't compare offset-naive and offset-aware
datetimes` — em runtime, no refresh de login e no reset de senha.

Por isso o helper devolve naive de propósito. Migrar as colunas para
TIMESTAMPTZ é o conserto de verdade, e é branch à parte.
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]

UTCNOW = re.compile(r"\butcnow\s*\(")


def test_agora_utc_devolve_naive():
    """Aware aqui quebraria a comparação com o que volta do banco."""
    from core.tempo import agora_utc

    assert agora_utc().tzinfo is None


def test_agora_utc_bate_com_o_relogio_utc():
    from core.tempo import agora_utc

    referencia = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs(agora_utc() - referencia) < timedelta(seconds=5)


def test_agora_utc_nao_usa_horario_local():
    """Se alguém trocar por datetime.now() sem tz, isto pega em qualquer TZ != UTC."""
    from core.tempo import agora_utc

    assert abs(agora_utc() - datetime.now(timezone.utc).replace(tzinfo=None)) < timedelta(minutes=1)


# core/tempo.py e este arquivo citam `utcnow()` em prosa para explicar o que
# substituem — a varredura é textual e não distingue código de docstring.
_ISENTOS = {"tempo.py", "test_tempo_utc.py"}


def _fontes_python():
    return [
        p for p in BACKEND.rglob("*.py")
        if "venv" not in p.parts and "__pycache__" not in p.parts and p.name not in _ISENTOS
    ]


@pytest.mark.parametrize("arquivo", _fontes_python(), ids=lambda p: p.name)
def test_nenhum_arquivo_usa_utcnow(arquivo):
    """`datetime.utcnow()` está deprecado e sai numa versão futura do Python."""
    texto = arquivo.read_text(encoding="utf-8")
    achados = [
        f"linha {n}: {linha.strip()[:100]}"
        for n, linha in enumerate(texto.splitlines(), 1)
        if UTCNOW.search(linha)
    ]
    assert not achados, (
        f"{arquivo.relative_to(BACKEND)} usa utcnow(). Use core.tempo.agora_utc():\n  "
        + "\n  ".join(achados)
    )
