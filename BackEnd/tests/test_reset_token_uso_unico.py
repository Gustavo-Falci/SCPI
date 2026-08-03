"""A4 — o reset_token vale uma única troca de senha.

Antes, era um JWT stateless de 15 min sem jti: dentro da janela servia para
trocar a senha quantas vezes o portador quisesse.
"""
import pytest
from datetime import timedelta

import jwt as _jwt
from fastapi import HTTPException

from core.tempo import agora_utc


def _token(jti, email="teste@exemplo.com", minutos=15):
    from core.auth_utils import ALGORITHM, SECRET_KEY

    payload = {
        "sub": email,
        "type": "password_reset",
        "exp": agora_utc() + timedelta(minutes=minutos),
    }
    if jti is not None:
        payload["jti"] = jti
    return _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_verificar_codigo_inclui_jti_no_token(monkeypatch):
    import routers.auth as auth

    monkeypatch.setattr(
        auth, "buscar_codigo_reset_valido",
        lambda _e, _h: {"id": 42, "expires_at": agora_utc() + timedelta(minutes=10)},
    )
    monkeypatch.setattr(auth, "marcar_codigo_reset_usado", lambda _id: 1)

    class _Body:
        email = "teste@exemplo.com"
        codigo = "123456"

    class _Request:
        client = type("C", (), {"host": "127.0.0.1"})()

    resultado = auth.verificar_codigo.__wrapped__(request=_Request(), body=_Body())

    from core.auth_utils import ALGORITHM, SECRET_KEY

    # jti é string (RFC 7519 — PyJWT valida o tipo no decode); o id numérico do
    # PasswordResetCodes é convertido de volta a int só no redefinir_senha,
    # logo antes do claim atômico.
    payload = _jwt.decode(resultado["reset_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["jti"] == "42"


def test_segundo_uso_do_mesmo_token_falha(monkeypatch):
    import routers.auth as auth

    consumidos = set()

    def _consumir(codigo_id):
        if codigo_id in consumidos:
            return False
        consumidos.add(codigo_id)
        return True

    senhas = []
    monkeypatch.setattr(auth, "consumir_token_reset", _consumir)
    monkeypatch.setattr(auth, "senha_comprometida", lambda _s: False)
    monkeypatch.setattr(auth, "atualizar_senha_por_email", lambda e, h: senhas.append(h))
    monkeypatch.setattr(auth, "buscar_usuario_id_por_email_lower", lambda _e: None)

    class _Body:
        reset_token = _token("42")
        nova_senha = "senha-nova-super-longa-1"

    class _Request:
        client = type("C", (), {"host": "127.0.0.1"})()

    auth.redefinir_senha(request=_Request(), body=_Body())
    assert len(senhas) == 1

    with pytest.raises(HTTPException) as exc:
        auth.redefinir_senha(request=_Request(), body=_Body())

    assert exc.value.status_code == 400
    assert len(senhas) == 1  # a segunda tentativa não trocou nada


def test_token_sem_jti_e_rejeitado(monkeypatch):
    import routers.auth as auth

    monkeypatch.setattr(auth, "consumir_token_reset", lambda _id: True)
    monkeypatch.setattr(auth, "senha_comprometida", lambda _s: False)

    class _Body:
        reset_token = _token(None)
        nova_senha = "senha-nova-super-longa-1"

    class _Request:
        client = type("C", (), {"host": "127.0.0.1"})()

    with pytest.raises(HTTPException) as exc:
        auth.redefinir_senha(request=_Request(), body=_Body())

    assert exc.value.status_code == 400


def test_mensagem_nao_revela_que_o_token_ja_foi_usado(monkeypatch):
    """Mensagem idêntica à de token expirado: dizer 'já usado' confirma ao
    atacante que aquele token existiu e foi válido."""
    import routers.auth as auth

    monkeypatch.setattr(auth, "consumir_token_reset", lambda _id: False)
    monkeypatch.setattr(auth, "senha_comprometida", lambda _s: False)

    class _Body:
        reset_token = _token("42")
        nova_senha = "senha-nova-super-longa-1"

    class _Request:
        client = type("C", (), {"host": "127.0.0.1"})()

    with pytest.raises(HTTPException) as exc:
        auth.redefinir_senha(request=_Request(), body=_Body())

    assert exc.value.detail == "Token inválido ou expirado."


def test_senha_recusada_pelo_hibp_nao_consome_o_token(monkeypatch):
    """Fix round 1 (Gustavo): consumir o token antes de checar a senha no HIBP
    queimaria o reset_token de quem só errou a senha na primeira tentativa,
    obrigando a pedir código novo por e-mail à toa. O claim atômico tem que vir
    depois das checagens que não escrevem nada — este teste fixa essa ordem.
    """
    import routers.auth as auth

    consumos = []

    def _consumir(codigo_id):
        consumos.append(codigo_id)
        return True

    senhas = []
    estado = {"comprometida": True}
    monkeypatch.setattr(auth, "consumir_token_reset", _consumir)
    monkeypatch.setattr(auth, "senha_comprometida", lambda _s: estado["comprometida"])
    monkeypatch.setattr(auth, "atualizar_senha_por_email", lambda e, h: senhas.append(h))
    monkeypatch.setattr(auth, "buscar_usuario_id_por_email_lower", lambda _e: None)

    token = _token("42")

    class _Body:
        reset_token = token
        nova_senha = "12345678"  # será recusada pelo HIBP na 1a tentativa

    class _Request:
        client = type("C", (), {"host": "127.0.0.1"})()

    with pytest.raises(HTTPException) as exc:
        auth.redefinir_senha(request=_Request(), body=_Body())

    assert exc.value.status_code == 400
    assert consumos == []  # token NÃO foi consumido pela senha recusada
    assert senhas == []

    # Mesmo token, agora com senha boa: continua válido.
    estado["comprometida"] = False
    _Body.nova_senha = "senha-nova-super-longa-1"
    auth.redefinir_senha(request=_Request(), body=_Body())

    assert consumos == [42]
    assert len(senhas) == 1  # senha foi de fato gravada na 2a tentativa
