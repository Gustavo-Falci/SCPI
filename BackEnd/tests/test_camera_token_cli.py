"""Banco fora não pode virar resposta confiante no CLI de tokens da câmera.

Antes, `listar_tokens` devolvia `[]` e `revogar_token` devolvia `False` quando o
pool não dava conexão — indistinguível de "nenhum token existe" e "token não
encontrado ou já revogado". O script imprimia as duas frases com o banco fora.

A segunda é a que dói: quem está revogando um token comprometido lê "já
revogado" e para de agir, com o token ainda válido.
"""
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from infra.database import DB_INDISPONIVEL


@contextmanager
def _sem_cursor():
    """Reproduz o pool sem conexão: get_db_cursor entrega None."""
    yield None


@pytest.fixture
def banco_fora(monkeypatch):
    from repositories import camera_tokens

    monkeypatch.setattr(camera_tokens, "get_db_cursor", lambda *a, **k: _sem_cursor())


def test_listar_com_banco_fora_devolve_sentinela(banco_fora):
    from repositories.camera_tokens import listar_tokens

    assert listar_tokens() is DB_INDISPONIVEL


def test_revogar_com_banco_fora_devolve_sentinela(banco_fora):
    from repositories.camera_tokens import revogar_token

    assert revogar_token(1) is DB_INDISPONIVEL


def test_sentinela_nao_e_confundivel_com_vazio():
    """`[]` e `False` são falsy; a sentinela não pode ser tratada como eles.

    O CLI decide por `is DB_INDISPONIVEL` ANTES de qualquer teste de verdade —
    este teste existe para pinar que a checagem não pode ser trocada por
    `if not resultado`.
    """
    assert DB_INDISPONIVEL is not None
    assert DB_INDISPONIVEL != []
    assert DB_INDISPONIVEL is not False


def _rodar_cli(monkeypatch, comando, **retornos):
    """Executa main() do script com os repositórios trocados por dublês.

    `_preparar` é neutralizado porque abre conexão de verdade: sem isso o teste
    tenta alcançar o DB_HOST do .env e paga um DB_CONNECT_TIMEOUT inteiro por
    caso — foi o que levou a suíte de 12s para 49s.
    """
    import sys

    import scripts.camera_token as cli

    monkeypatch.setattr(cli, "_preparar", lambda: None)
    for nome, valor in retornos.items():
        monkeypatch.setattr(cli, nome, MagicMock(return_value=valor))
    monkeypatch.setattr(sys, "argv", ["camera_token.py", *comando])
    return cli


def test_cli_listar_com_banco_fora_sai_com_erro(monkeypatch, capsys):
    cli = _rodar_cli(monkeypatch, ["listar"], listar_tokens=DB_INDISPONIVEL)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    saida = capsys.readouterr()
    assert "banco indisponível" in saida.err
    assert "Nenhum token emitido" not in saida.out


def test_cli_revogar_com_banco_fora_diz_que_nao_revogou(monkeypatch, capsys):
    """A mensagem precisa ser inequívoca — o operador vai agir com base nela."""
    cli = _rodar_cli(monkeypatch, ["revogar", "--id", "7"], revogar_token=DB_INDISPONIVEL)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    erro = capsys.readouterr().err
    assert "NÃO foi revogado" in erro
    assert "já revogado" not in erro


def test_cli_revogar_inexistente_continua_dizendo_nao_encontrado(monkeypatch, capsys):
    """Regressão: o caso legítimo não pode ter sido engolido pela sentinela."""
    cli = _rodar_cli(monkeypatch, ["revogar", "--id", "7"], revogar_token=False)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    assert "não encontrado ou já revogado" in capsys.readouterr().err


def test_cli_revogar_com_sucesso_sai_zero(monkeypatch, capsys):
    cli = _rodar_cli(monkeypatch, ["revogar", "--id", "7"], revogar_token=True)

    cli.main()  # não levanta SystemExit

    assert "Token 7 revogado." in capsys.readouterr().out


def test_cli_traduz_excecao_do_banco_em_mensagem(monkeypatch, capsys):
    """`emitir_token` levanta com banco fora; traceback cru não ajuda operação."""
    import sys

    import scripts.camera_token as cli

    monkeypatch.setattr(cli, "_preparar", lambda: None)
    monkeypatch.setattr(
        cli, "emitir_token",
        MagicMock(side_effect=RuntimeError("Banco indisponível para emitir token.")),
    )
    monkeypatch.setattr(sys, "argv", ["camera_token.py", "emitir", "--sala", "Sala 1"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    erro = capsys.readouterr().err
    assert "RuntimeError" in erro
    assert "Banco indisponível para emitir token." in erro
