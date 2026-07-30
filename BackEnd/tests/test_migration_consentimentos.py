"""Testes da migration ConsentimentosLGPD (sem DB real)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from infra.migrations import ensure_consentimentos_table


def _run(func):
    executed = []
    cur = MagicMock()
    cur.execute.side_effect = lambda *a, **k: executed.append(a[0])

    @contextmanager
    def fake_cursor(commit=False):
        yield cur

    with patch("infra.migrations.get_db_cursor", fake_cursor):
        func()
    return " ".join(executed)


def test_cria_tabela_e_indice():
    sql = _run(ensure_consentimentos_table)
    assert "CREATE TABLE IF NOT EXISTS ConsentimentosLGPD" in sql
    assert "idx_consent_aluno" in sql


def test_tem_todas_as_colunas():
    sql = _run(ensure_consentimentos_table)
    for coluna in ["aluno_id", "evento", "politica_versao", "registrado_em",
                   "ip", "user_agent", "origem"]:
        assert coluna in sql


def test_backfill_marca_origem_e_versao_legado():
    sql = _run(ensure_consentimentos_table)
    assert "'backfill'" in sql
    assert "'legado'" in sql


def test_backfill_e_idempotente():
    # NOT EXISTS impede duplicar quando os 4 workers gunicorn rodam a etapa.
    sql = _run(ensure_consentimentos_table)
    assert "NOT EXISTS" in sql


def test_backfill_ignora_biometria_revogada():
    sql = _run(ensure_consentimentos_table)
    assert "revogado_em IS NULL" in sql


def test_registrada_em_etapas():
    from infra.migrations import _ETAPAS
    assert "ensure_consentimentos_table" in _ETAPAS
