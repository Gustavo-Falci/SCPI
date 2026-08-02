"""Índices do caminho quente da câmera e dos relatórios existem após a migration."""
import pytest

_INDICES = [
    "idx_horarios_sala_dia",
    "idx_horarios_turma",
    "idx_presencas_aluno",
    "idx_chamadas_turma_status",
    "idx_chamadas_professor",
    "idx_chamadas_data",
]


@pytest.mark.parametrize("indice", _INDICES)
def test_indice_criado(pg, indice):
    from infra.database import get_db_cursor
    from infra.migrations import ensure_base_schema, ensure_indices_performance

    ensure_base_schema()
    ensure_indices_performance()

    with get_db_cursor() as cur:
        cur.execute("SELECT 1 FROM pg_indexes WHERE indexname = %s", (indice,))
        assert cur.fetchone() is not None, f"índice {indice} não foi criado"


def test_migration_e_idempotente(pg):
    """Rodar duas vezes não pode explodir — o boot chama todas as etapas sempre."""
    from infra.migrations import ensure_base_schema, ensure_indices_performance

    ensure_base_schema()
    ensure_indices_performance()
    ensure_indices_performance()


def test_indice_da_camera_e_usado(pg):
    """O índice existir não basta: o planner tem que escolhê-lo.

    Este é o índice que justifica a alteração — a query da câmera roda a cada
    burst. Com seq_scan desligado o EXPLAIN acusa se o índice não casa com o
    predicado (ordem das colunas, tipo de dia_semana).
    """
    from infra.database import get_db_cursor
    from infra.migrations import ensure_base_schema, ensure_indices_performance

    ensure_base_schema()
    ensure_indices_performance()

    with get_db_cursor() as cur:
        cur.execute("SET LOCAL enable_seqscan = off")
        cur.execute(
            """
            EXPLAIN SELECT 1 FROM horarios_aulas
            WHERE sala = %s AND dia_semana = 1
            """,
            ("A101",),
        )
        plano = " ".join(str(linha["QUERY PLAN"]) for linha in cur.fetchall())

    assert "idx_horarios_sala_dia" in plano, plano


def test_etapa_registrada_no_pipeline():
    """Sem estar em _ETAPAS, a migration nunca roda no boot. Não precisa de banco."""
    from infra.migrations import _ETAPAS

    assert "ensure_indices_performance" in _ETAPAS
