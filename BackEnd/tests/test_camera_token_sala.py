"""A6 — o token de serviço passa a carregar a sala.

Antes era um token global vindo de env: vazado numa sala, marcava presença em
qualquer chamada de qualquer sala.
"""
import pytest
from fastapi import HTTPException


class _Request:
    url = type("U", (), {"path": "/chamadas/aberta/sala"})()
    client = type("C", (), {"host": "127.0.0.1"})()


def test_token_valido_devolve_a_sala(monkeypatch):
    import core.security as security

    monkeypatch.setattr(
        security, "buscar_sala_por_token",
        lambda t: "Sala 101" if t == "token-bom" else None,
    )

    assert security.require_service_token(_Request(), "token-bom") == "Sala 101"


def test_token_desconhecido_e_403(monkeypatch):
    import core.security as security

    monkeypatch.setattr(security, "buscar_sala_por_token", lambda _t: None)

    with pytest.raises(HTTPException) as exc:
        security.require_service_token(_Request(), "token-ruim")

    assert exc.value.status_code == 403


def test_hash_do_token_nao_e_o_token(monkeypatch):
    from repositories.camera_tokens import hash_camera_token

    h = hash_camera_token("token-bom")

    assert h != "token-bom"
    assert len(h) == 64  # sha256 hex
    assert hash_camera_token("token-bom") == h  # determinístico


def test_banco_indisponivel_e_503_nao_403(monkeypatch):
    """Achar do review pós-A6: `get_db_cursor` devolve None tanto para "token
    desconhecido" quanto para "banco fora do ar", e a câmera trata 4xx como
    recusa definitiva (nunca mais tenta aquele aluno nesta chamada). Um blip
    de banco não pode ter o mesmo efeito que um token revogado — tem que
    sair como 503 (transitório), não 403."""
    import core.security as security
    from infra.database import DB_INDISPONIVEL

    monkeypatch.setattr(security, "buscar_sala_por_token", lambda _t: DB_INDISPONIVEL)

    with pytest.raises(HTTPException) as exc:
        security.require_service_token(_Request(), "qualquer-token")

    assert exc.value.status_code == 503


def test_banco_indisponivel_nao_gera_warning_de_token_invalido(monkeypatch, caplog):
    """O 503 não pode poluir a trilha de auditoria com falsos positivos de
    "token inválido" — isso degradaria justamente o sinal que A6 quis dar
    para detectar um token vazado."""
    import logging

    import core.security as security
    from infra.database import DB_INDISPONIVEL

    monkeypatch.setattr(security, "buscar_sala_por_token", lambda _t: DB_INDISPONIVEL)

    with caplog.at_level(logging.WARNING, logger="scpi.audit"):
        with pytest.raises(HTTPException):
            security.require_service_token(_Request(), "qualquer-token")

    assert not any(
        "Token de serviço inválido" in registro.getMessage() for registro in caplog.records
    )


def test_buscar_sala_devolve_sentinela_quando_cursor_indisponivel(monkeypatch):
    """Nível de repositório: sem mockar `require_service_token`, confirma que
    é `buscar_sala_por_token` quem já distingue as duas situações."""
    from contextlib import contextmanager

    import repositories.camera_tokens as camera_tokens
    from infra.database import DB_INDISPONIVEL

    @contextmanager
    def _cursor_indisponivel(commit=False):
        yield None

    monkeypatch.setattr(camera_tokens, "get_db_cursor", _cursor_indisponivel)

    assert camera_tokens.buscar_sala_por_token("token-qualquer") is DB_INDISPONIVEL
