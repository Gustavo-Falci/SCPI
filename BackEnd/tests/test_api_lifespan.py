"""O lifespan da API roda startup e shutdown de verdade.

Os `@app.on_event` viraram um `@asynccontextmanager` passado ao construtor do
FastAPI. Nenhum outro teste exercita esse caminho: todos usam `TestClient(app)`
SEM `with`, e nessa forma o lifespan não é disparado. Ou seja, um erro no boot
só apareceria no `systemctl restart` em produção, com a API fora do ar.

Aqui o TestClient é usado como context manager justamente para forçar a
execução, com as quatro dependências externas (migrations, agendador, AWS e
pool) trocadas por dublês.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient


async def _agendador_falso():
    """O startup faz asyncio.create_task(iniciar_agendador()) — precisa de corrotina."""
    return None


def _dubles():
    return (
        patch("api._migrations.run_all"),
        patch("api.iniciar_agendador", _agendador_falso),
        patch("api._check_aws_connectivity"),
        patch("api.close_pool"),
    )


def test_startup_roda_migrations_e_checa_aws():
    from api import app

    p_mig, p_agen, p_aws, p_pool = _dubles()
    with p_mig as run_all, p_agen, p_aws as check_aws, p_pool:
        with TestClient(app):
            pass

    run_all.assert_called_once()
    check_aws.assert_called_once()


def test_shutdown_fecha_o_pool():
    from api import app

    p_mig, p_agen, p_aws, p_pool = _dubles()
    with p_mig, p_agen, p_aws, p_pool as close_pool:
        with TestClient(app):
            close_pool.assert_not_called()  # ainda no ar
    close_pool.assert_called_once()


def test_shutdown_cancela_a_task_do_agendador():
    import api

    p_mig, p_agen, p_aws, p_pool = _dubles()
    with p_mig, p_agen, p_aws, p_pool:
        with TestClient(api.app):
            assert api._agendador_task is not None

    assert api._agendador_task.cancelled() or api._agendador_task.done(), (
        "task do agendador ficou viva depois do shutdown"
    )


def test_falha_no_startup_nao_sobe_a_aplicacao():
    """run_all() estourando tem de derrubar o boot, não subir a API pela metade.

    É o contrato de migrations fail-loud: schema desatualizado não pode virar
    500 espalhado pelos endpoints.
    """
    from api import app

    p_mig, p_agen, p_aws, p_pool = _dubles()
    with p_mig as run_all, p_agen, p_aws, p_pool:
        run_all.side_effect = RuntimeError("migration quebrada")
        try:
            with TestClient(app):
                pass
        except RuntimeError as exc:
            assert "migration quebrada" in str(exc)
        else:
            raise AssertionError("o boot deveria ter propagado o erro da migration")
