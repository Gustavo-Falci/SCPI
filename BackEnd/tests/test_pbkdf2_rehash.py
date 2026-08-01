"""A3 — política de iterações do pbkdf2 e migração transparente no login.

Hashes antigos (29k iterações, o default do passlib) precisam continuar
autenticando e ser regravados com a política atual no primeiro login.
"""
from passlib.context import CryptContext


def test_politica_usa_600k_iteracoes():
    from core.auth_utils import _PBKDF2_ROUNDS, get_password_hash

    assert _PBKDF2_ROUNDS == 600_000
    # Formato: $pbkdf2-sha256$<rounds>$<salt>$<checksum>
    assert get_password_hash("senha-de-teste-12345").split("$")[2] == "600000"


def test_hash_legado_autentica_e_devolve_hash_novo():
    from core.auth_utils import _PBKDF2_ROUNDS, verificar_e_atualizar_senha

    legado = CryptContext(schemes=["pbkdf2_sha256"], pbkdf2_sha256__rounds=29000)
    hash_antigo = legado.hash("senha-de-teste-12345")

    ok, hash_novo = verificar_e_atualizar_senha("senha-de-teste-12345", hash_antigo)

    assert ok is True
    assert hash_novo is not None
    assert hash_novo.split("$")[2] == str(_PBKDF2_ROUNDS)


def test_hash_atual_autentica_sem_regravar():
    from core.auth_utils import get_password_hash, verificar_e_atualizar_senha

    ok, hash_novo = verificar_e_atualizar_senha(
        "senha-de-teste-12345", get_password_hash("senha-de-teste-12345")
    )

    assert ok is True
    assert hash_novo is None


def test_senha_errada_nao_dispara_rehash():
    legado = CryptContext(schemes=["pbkdf2_sha256"], pbkdf2_sha256__rounds=29000)
    hash_antigo = legado.hash("senha-de-teste-12345")

    from core.auth_utils import verificar_e_atualizar_senha

    ok, hash_novo = verificar_e_atualizar_senha("senha-errada-99999", hash_antigo)

    assert ok is False
    assert hash_novo is None


def test_dummy_hash_usa_a_politica_atual():
    """Se o hash descartável ficar em 29k, o caminho de usuário inexistente
    responde ~20x mais rápido que o de senha errada e a defesa de timing do
    pentest de 2026-05-25 vira oráculo de enumeração."""
    from core.auth_utils import _PBKDF2_ROUNDS
    from routers.auth import _DUMMY_PASSWORD_HASH

    assert _DUMMY_PASSWORD_HASH.split("$")[2] == str(_PBKDF2_ROUNDS)


def test_login_persiste_hash_novo_quando_legado(monkeypatch):
    """Wiring: o login precisa gravar o hash migrado, senão a migração nunca sai
    do lugar e todo login paga a verificação em 29k para sempre."""
    from fastapi import Response
    from passlib.context import CryptContext

    import routers.auth as auth

    legado = CryptContext(schemes=["pbkdf2_sha256"], pbkdf2_sha256__rounds=29000)
    usuario = {
        "usuario_id": "11111111-1111-1111-1111-111111111111",
        "nome": "Teste",
        "email": "teste@exemplo.com",
        "senha": legado.hash("senha-de-teste-12345"),
        "tipo_usuario": "Professor",
        "primeiro_acesso": False,
    }

    gravados = []

    monkeypatch.setattr(auth, "esta_bloqueado", lambda _e: False)
    monkeypatch.setattr(auth, "registrar_falha", lambda _e: None)
    monkeypatch.setattr(auth, "limpar_falhas", lambda _e: None)
    monkeypatch.setattr(auth, "buscar_usuario_login_por_email", lambda _e: usuario)
    monkeypatch.setattr(auth, "inserir_refresh_token", lambda *_a: True)
    monkeypatch.setattr(auth, "atualizar_hash_senha", lambda uid, h: gravados.append((uid, h)))

    class _FormData:
        username = "teste@exemplo.com"
        password = "senha-de-teste-12345"

    class _Request:
        client = type("C", (), {"host": "127.0.0.1"})()

    auth.login.__wrapped__(
        request=_Request(), response=Response(), form_data=_FormData()
    )

    assert len(gravados) == 1
    assert gravados[0][1].split("$")[2] == "600000"
