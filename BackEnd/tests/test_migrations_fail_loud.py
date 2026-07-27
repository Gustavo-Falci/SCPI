"""Migration que falha derruba o boot em vez de logar e seguir.

Schema incompleto com a API no ar produz 500s aleatórios longe da causa; é pior
que não subir. Mesmo precedente do SCPI_EXPORT_HMAC_KEY ausente.
"""
from unittest.mock import MagicMock, patch

import pytest

import infra.migrations as m


def test_apply_all_propaga_erro_com_nome_da_etapa():
    def explode():
        raise RuntimeError("coluna já existe com outro tipo")

    # As demais etapas (não mockadas individualmente) precisam de um cursor
    # fake para não tocar banco real — sem SCPI_RUN_DB_TESTS=1, get_db_cursor
    # real cairia no DB_HOST do .env de dev (produção, ver tests/conftest.py).
    fake_cur = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = fake_cur
    ctx.__exit__.return_value = False

    with patch.object(m, "get_db_cursor", return_value=ctx):
        with patch.object(m, "ensure_push_tokens_table", explode):
            with pytest.raises(RuntimeError) as exc:
                m._apply_all()

    assert "ensure_push_tokens_table" in str(exc.value)


def test_run_all_levanta_quando_nao_ha_conexao():
    with patch("infra.migrations._db.get_db_connection", return_value=None):
        with pytest.raises(RuntimeError, match="sem conexão com o banco"):
            m.run_all()


def test_etapas_cobrem_todas_as_funcoes_ensure():
    """A lista de etapas não pode ficar para trás quando alguém adiciona uma migration."""
    definidas = {n for n in dir(m) if n.startswith("ensure_")}
    assert definidas == set(m._ETAPAS)


def test_run_all_aplica_schema_completo(pg):
    """Migrations rodam de ponta a ponta contra Postgres real (CI, opt-in).

    Os demais testes deste arquivo mockam o cursor e só validam a fiação
    (nome da etapa, propagação de erro); nenhum executa o SQL de verdade.
    Roda apenas com SCPI_RUN_DB_TESTS=1 (serviço postgres:16 do CI) — local,
    sem a flag, pula (ver tests/conftest.py:_db_disponivel). Não conecta a
    banco nenhum sem esse opt-in explícito.
    """
    from infra.migrations import run_all

    run_all()
    run_all()  # idempotência


def test_ensure_base_schema_e_a_primeira_etapa():
    """A comparação por conjunto acima não pega reordenação: mover
    ensure_base_schema para fora da primeira posição passaria no teste acima e
    quebraria o boot num banco novo, porque toda outra etapa faz ALTER TABLE em
    tabelas que só ensure_base_schema cria.
    """
    assert m._ETAPAS[0] == "ensure_base_schema"
