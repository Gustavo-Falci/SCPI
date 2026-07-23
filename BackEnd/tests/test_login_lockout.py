import pytest

from infra.database import get_db_cursor
from repositories import auth_lockout as al

pytestmark = pytest.mark.usefixtures("pg")


def test_nao_bloqueia_antes_do_limite():
    email = "a@x.com"
    for _ in range(al.MAX_FAILS - 1):
        al.registrar_falha(email)
        assert al.esta_bloqueado(email) is None


def test_bloqueia_ao_atingir_o_limite():
    email = "b@x.com"
    for _ in range(al.MAX_FAILS):
        al.registrar_falha(email)
    assert al.esta_bloqueado(email) is not None


def test_limpar_falhas_zera_contagem():
    email = "c@x.com"
    al.registrar_falha(email)
    al.registrar_falha(email)
    al.limpar_falhas(email)
    fails, locked = al.registrar_falha(email)
    assert fails == 1
    assert locked is None


def test_lock_expirado_libera():
    email = "d@x.com"
    for _ in range(al.MAX_FAILS):
        al.registrar_falha(email)
    assert al.esta_bloqueado(email) is not None
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE login_attempts SET locked_until = now() - interval '1 minute' "
            "WHERE email=%s",
            (email,),
        )
    assert al.esta_bloqueado(email) is None


def test_janela_expirada_reinicia_contagem():
    email = "e@x.com"
    al.registrar_falha(email)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE login_attempts SET first_fail_at = now() - interval '20 minutes' "
            "WHERE email=%s",
            (email,),
        )
    fails, _ = al.registrar_falha(email)
    assert fails == 1


def test_purgar_remove_antigos_desbloqueados():
    email = "f@x.com"
    al.registrar_falha(email)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE login_attempts SET first_fail_at = now() - interval '2 days', "
            "locked_until = NULL WHERE email=%s",
            (email,),
        )
    assert al.purgar_login_attempts() >= 1
