"""A migração que remove a coluna departamento existe, roda o DROP e está no pipeline."""
from unittest.mock import MagicMock, patch

import infra.migrations as m


def test_funcao_existe_e_registrada_no_pipeline():
    assert hasattr(m, "ensure_professor_departamento_dropped")

    called = []
    # substitui cada ensure_* por um stub que registra o nome chamado
    names = [n for n in dir(m) if n.startswith("ensure_")]
    patchers = {n: patch.object(m, n, lambda _n=n: called.append(_n)) for n in names}
    for p in patchers.values():
        p.start()
    try:
        m._apply_all()
    finally:
        for p in patchers.values():
            p.stop()

    assert "ensure_professor_departamento_dropped" in called


def test_drop_executa_alter_table():
    fake_cur = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = fake_cur
    ctx.__exit__.return_value = False

    with patch.object(m, "get_db_cursor", return_value=ctx):
        m.ensure_professor_departamento_dropped()

    executed = " ".join(call.args[0] for call in fake_cur.execute.call_args_list).lower()
    assert "alter table professores" in executed
    assert "drop column if exists departamento" in executed
