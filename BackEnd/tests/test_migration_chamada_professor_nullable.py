"""A migração que torna chamadas.professor_id nullable existe, roda e está no pipeline.

Regressão: excluir professor com chamada dava NotNullViolation ao orfanar a
chamada (UPDATE Chamadas SET professor_id = NULL). A coluna precisa ser nullable,
espelhando turmas.professor_id.
"""
from unittest.mock import MagicMock, patch

import infra.migrations as m


def test_funcao_existe_e_registrada_no_pipeline():
    assert hasattr(m, "ensure_chamada_professor_nullable")

    called = []
    names = [n for n in dir(m) if n.startswith("ensure_")]
    patchers = {n: patch.object(m, n, lambda _n=n: called.append(_n)) for n in names}
    for p in patchers.values():
        p.start()
    try:
        m._apply_all()
    finally:
        for p in patchers.values():
            p.stop()

    assert "ensure_chamada_professor_nullable" in called


def test_migration_executa_drop_not_null():
    fake_cur = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = fake_cur
    ctx.__exit__.return_value = False

    with patch.object(m, "get_db_cursor", return_value=ctx):
        m.ensure_chamada_professor_nullable()

    executed = " ".join(call.args[0] for call in fake_cur.execute.call_args_list).lower()
    assert "alter table chamadas" in executed
    assert "alter column professor_id drop not null" in executed
