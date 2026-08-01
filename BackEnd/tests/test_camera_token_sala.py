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
