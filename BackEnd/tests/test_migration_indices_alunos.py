"""Os índices que sustentam os filtros da aba Alunos existem após a migration."""
import pytest


@pytest.mark.parametrize("indice", ["idx_turma_alunos_aluno", "idx_turmas_semestre"])
def test_indice_criado(pg, indice):
    from infra.database import get_db_cursor
    from infra.migrations import ensure_base_schema, ensure_indices_filtros_alunos

    # A fixture pg só garante as tabelas de rate limit; o schema acadêmico e os
    # índices vêm destas duas etapas.
    ensure_base_schema()
    ensure_indices_filtros_alunos()

    with get_db_cursor() as cur:
        cur.execute("SELECT 1 FROM pg_indexes WHERE indexname = %s", (indice,))
        assert cur.fetchone() is not None, f"índice {indice} não foi criado"


def test_migration_e_idempotente(pg):
    """Rodar duas vezes não pode explodir — o boot chama todas as etapas sempre."""
    from infra.migrations import ensure_base_schema, ensure_indices_filtros_alunos

    ensure_base_schema()
    ensure_indices_filtros_alunos()
    ensure_indices_filtros_alunos()


def test_etapa_registrada_no_pipeline():
    """Sem estar em _ETAPAS, a migration nunca roda no boot. Não precisa de banco."""
    from infra.migrations import _ETAPAS

    assert "ensure_indices_filtros_alunos" in _ETAPAS
