"""Testes de push: repositório, infra (tickets) e wiring de service — sem DB/rede real."""
import io
import json
from unittest.mock import MagicMock, patch


def _mock_cursor():
    cur = MagicMock()
    cur.fetchone.return_value = None
    cur.fetchall.return_value = []
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return cm, cur


def _mock_urlopen_data(data):
    resp = MagicMock()
    resp.read.return_value = json.dumps({"data": data}).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = False
    return cm


A = "ExponentPushToken[a]"
B = "ExponentPushToken[b]"
C = "ExponentPushToken[c]"


def test_remover_push_token_faz_delete_por_token():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm):
        from repositories.notificacoes import remover_push_token
        remover_push_token("ExponentPushToken[a]")
    sql, params = cur.execute.call_args[0]
    assert "DELETE FROM PushTokens" in sql
    assert "expo_token = %s" in sql
    assert params == ("ExponentPushToken[a]",)


def test_send_todos_ok():
    cm = _mock_urlopen_data([{"status": "ok", "id": "1"}, {"status": "ok", "id": "2"}])
    with patch("infra.notificacoes.urllib.request.urlopen", return_value=cm):
        from infra.notificacoes import send_expo_push
        out = send_expo_push([A, B], "t", "b")
    assert out == {
        "ok": [A, B],
        "dead": [],
        "tickets": [{"id": "1", "token": A}, {"id": "2", "token": B}],
    }


def test_send_device_not_registered_vai_para_dead():
    cm = _mock_urlopen_data([
        {"status": "ok", "id": "1"},
        {"status": "error", "message": "x", "details": {"error": "DeviceNotRegistered"}},
    ])
    with patch("infra.notificacoes.urllib.request.urlopen", return_value=cm):
        from infra.notificacoes import send_expo_push
        out = send_expo_push([A, B], "t", "b")
    assert out == {"ok": [A], "dead": [B], "tickets": [{"id": "1", "token": A}]}


def test_send_erro_transitorio_nao_poda():
    cm = _mock_urlopen_data([
        {"status": "error", "message": "x", "details": {"error": "MessageRateExceeded"}},
    ])
    with patch("infra.notificacoes.urllib.request.urlopen", return_value=cm):
        from infra.notificacoes import send_expo_push
        out = send_expo_push([A], "t", "b")
    assert out == {"ok": [], "dead": [], "tickets": []}


def test_send_httperror_retorno_vazio():
    import urllib.error
    err = urllib.error.HTTPError("u", 500, "erro", {}, io.BytesIO(b"boom"))
    with patch("infra.notificacoes.urllib.request.urlopen", side_effect=err):
        from infra.notificacoes import send_expo_push
        out = send_expo_push([A], "t", "b")
    assert out == {"ok": [], "dead": [], "tickets": []}


def test_send_contagem_divergente_nao_poda():
    cm = _mock_urlopen_data([{"status": "ok", "id": "1"}])  # 1 ticket p/ 2 tokens
    with patch("infra.notificacoes.urllib.request.urlopen", return_value=cm):
        from infra.notificacoes import send_expo_push
        out = send_expo_push([A, B], "t", "b")
    assert out == {"ok": [], "dead": [], "tickets": []}


def test_send_sem_token_valido_nao_faz_request():
    with patch("infra.notificacoes.urllib.request.urlopen") as m:
        from infra.notificacoes import send_expo_push
        out = send_expo_push(["lixo", None, ""], "t", "b")
    assert out == {"ok": [], "dead": [], "tickets": []}
    m.assert_not_called()


def test_presenca_poda_token_morto():
    with patch("services.notificacoes.obter_push_token_por_usuario",
               return_value={"expo_token": A}), \
         patch("services.notificacoes.send_expo_push",
               return_value={"ok": [], "dead": [A]}), \
         patch("services.notificacoes.remover_push_token") as rm, \
         patch("services.notificacoes.send_email_resend"):
        from services.notificacoes import enviar_notificacoes_presenca
        enviar_notificacoes_presenca("u1", "Ana", "", "Turma X")
    rm.assert_called_once_with(A)


def test_notificar_alunos_um_unico_request_com_todos_tokens():
    alunos = [
        {"usuario_id": "u1", "expo_token": A},
        {"usuario_id": "u2", "expo_token": B},
        {"usuario_id": "u3", "expo_token": C},
    ]
    with patch("services.notificacoes.obter_turma_id_por_chamada", return_value="t1"), \
         patch("services.notificacoes.listar_alunos_com_push_token_da_turma", return_value=alunos), \
         patch("services.notificacoes.send_expo_push",
               return_value={"ok": [A, B, C], "dead": []}) as m, \
         patch("services.notificacoes.remover_push_token") as rm:
        from services.notificacoes import notificar_alunos_presentes
        notificar_alunos_presentes("c1", "Turma X")
    assert m.call_count == 1
    assert m.call_args[0][0] == [A, B, C]
    rm.assert_not_called()


def test_notificar_alunos_poda_os_mortos():
    alunos = [
        {"usuario_id": "u1", "expo_token": A},
        {"usuario_id": "u2", "expo_token": C},
    ]
    with patch("services.notificacoes.obter_turma_id_por_chamada", return_value="t1"), \
         patch("services.notificacoes.listar_alunos_com_push_token_da_turma", return_value=alunos), \
         patch("services.notificacoes.send_expo_push",
               return_value={"ok": [A], "dead": [C]}), \
         patch("services.notificacoes.remover_push_token") as rm:
        from services.notificacoes import notificar_alunos_presentes
        notificar_alunos_presentes("c1", "Turma X")
    rm.assert_called_once_with(C)
