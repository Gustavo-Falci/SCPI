"""Testes de receipts assíncronos: migração, repo, infra, job — sem DB/rede real."""
import inspect
import io
import json
from unittest.mock import MagicMock, patch


def _mock_cursor():
    cur = MagicMock()
    cur.rowcount = 0
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


def test_ensure_push_receipts_table_cria_tabela():
    cm, cur = _mock_cursor()
    with patch("infra.migrations.get_db_cursor", return_value=cm):
        from infra.migrations import ensure_push_receipts_table
        ensure_push_receipts_table()
    sql = cur.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS PushReceiptsPendentes" in sql


def test_apply_all_registra_receipts():
    import infra.migrations as m
    assert "ensure_push_receipts_table()" in inspect.getsource(m._apply_all)


def test_registrar_tickets_pendentes_insere_com_on_conflict():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm), \
         patch("repositories.notificacoes.execute_values") as ev:
        from repositories.notificacoes import registrar_tickets_pendentes
        registrar_tickets_pendentes([{"id": "tk1", "token": "ExponentPushToken[a]"}])
    sql = ev.call_args[0][1]
    valores = ev.call_args[0][2]
    assert "INSERT INTO PushReceiptsPendentes" in sql
    assert "ON CONFLICT (ticket_id) DO NOTHING" in sql
    assert valores == [("tk1", "ExponentPushToken[a]")]
    assert "%" not in sql.replace("%s", "").replace("%%", "")


def test_registrar_tickets_pendentes_vazio_nao_insere():
    with patch("repositories.notificacoes.execute_values") as ev:
        from repositories.notificacoes import registrar_tickets_pendentes
        registrar_tickets_pendentes([])
    ev.assert_not_called()


def test_listar_tickets_pendentes_filtra_idade_e_limita():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm):
        from repositories.notificacoes import listar_tickets_pendentes
        listar_tickets_pendentes(900, 1000)
    sql, params = cur.execute.call_args[0]
    assert "FROM PushReceiptsPendentes" in sql
    assert "created_at <=" in sql
    assert "LIMIT %s" in sql
    assert params == (900, 1000)
    assert "%" not in sql.replace("%s", "").replace("%%", "")


def test_remover_tickets_pendentes_usa_any():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm):
        from repositories.notificacoes import remover_tickets_pendentes
        remover_tickets_pendentes(["tk1", "tk2"])
    sql, params = cur.execute.call_args[0]
    assert "DELETE FROM PushReceiptsPendentes" in sql
    assert "ticket_id = ANY(%s)" in sql
    assert params == (["tk1", "tk2"],)


def test_remover_tickets_pendentes_vazio_nao_executa():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm):
        from repositories.notificacoes import remover_tickets_pendentes
        remover_tickets_pendentes([])
    cur.execute.assert_not_called()


def test_remover_tickets_pendentes_antigos_por_idade():
    cm, cur = _mock_cursor()
    with patch("repositories.notificacoes.get_db_cursor", return_value=cm):
        from repositories.notificacoes import remover_tickets_pendentes_antigos
        remover_tickets_pendentes_antigos(86400)
    sql, params = cur.execute.call_args[0]
    assert "DELETE FROM PushReceiptsPendentes" in sql
    assert "created_at <=" in sql
    assert params == (86400,)
    assert "%" not in sql.replace("%s", "").replace("%%", "")


def test_send_expo_push_expoe_tickets_ok():
    tokens = ["ExponentPushToken[a]", "ExponentPushToken[b]"]
    cm = _mock_urlopen_data([{"status": "ok", "id": "tk1"}, {"status": "ok", "id": "tk2"}])
    with patch("infra.notificacoes.urllib.request.urlopen", return_value=cm):
        from infra.notificacoes import send_expo_push
        out = send_expo_push(tokens, "t", "b")
    assert out["tickets"] == [
        {"id": "tk1", "token": "ExponentPushToken[a]"},
        {"id": "tk2", "token": "ExponentPushToken[b]"},
    ]


def test_send_expo_push_ticket_ok_sem_id_nao_entra_em_tickets():
    cm = _mock_urlopen_data([{"status": "ok"}])  # sem id
    with patch("infra.notificacoes.urllib.request.urlopen", return_value=cm):
        from infra.notificacoes import send_expo_push
        out = send_expo_push(["ExponentPushToken[a]"], "t", "b")
    assert out["ok"] == ["ExponentPushToken[a]"]
    assert out["tickets"] == []


def test_send_expo_push_falha_transporte_tickets_vazio():
    import urllib.error
    err = urllib.error.HTTPError("u", 500, "erro", {}, io.BytesIO(b"x"))
    with patch("infra.notificacoes.urllib.request.urlopen", side_effect=err):
        from infra.notificacoes import send_expo_push
        out = send_expo_push(["ExponentPushToken[a]"], "t", "b")
    assert out == {"ok": [], "dead": [], "tickets": []}


def test_consultar_receipts_parseia_data():
    cm = _mock_urlopen_data({"tk1": {"status": "ok"},
                             "tk2": {"status": "error", "details": {"error": "DeviceNotRegistered"}}})
    with patch("infra.notificacoes.urllib.request.urlopen", return_value=cm):
        from infra.notificacoes import consultar_receipts
        out = consultar_receipts(["tk1", "tk2"])
    assert out["tk1"] == {"status": "ok"}
    assert out["tk2"]["details"]["error"] == "DeviceNotRegistered"


def test_consultar_receipts_faz_chunk_de_1000():
    ids = [f"tk{i}" for i in range(1500)]
    resp1 = _mock_urlopen_data({"tk0": {"status": "ok"}})
    resp2 = _mock_urlopen_data({"tk1000": {"status": "ok"}})
    with patch("infra.notificacoes.urllib.request.urlopen", side_effect=[resp1, resp2]) as m:
        from infra.notificacoes import consultar_receipts
        out = consultar_receipts(ids)
    assert m.call_count == 2
    assert "tk0" in out and "tk1000" in out


def test_consultar_receipts_httperror_nao_derruba():
    import urllib.error
    err = urllib.error.HTTPError("u", 500, "erro", {}, io.BytesIO(b"x"))
    with patch("infra.notificacoes.urllib.request.urlopen", side_effect=err):
        from infra.notificacoes import consultar_receipts
        out = consultar_receipts(["tk1"])
    assert out == {}


PEND = [
    {"ticket_id": "tk1", "expo_token": "ExponentPushToken[a]"},
    {"ticket_id": "tk2", "expo_token": "ExponentPushToken[b]"},
    {"ticket_id": "tk3", "expo_token": "ExponentPushToken[c]"},
]


def test_processar_device_not_registered_poda_e_processa():
    receipts = {"tk1": {"status": "error", "details": {"error": "DeviceNotRegistered"}}}
    from scripts.verificar_receipts import processar
    podar, processados = processar(PEND, receipts)
    assert podar == ["ExponentPushToken[a]"]
    assert processados == ["tk1"]


def test_processar_ok_nao_poda_mas_processa():
    receipts = {"tk2": {"status": "ok"}}
    from scripts.verificar_receipts import processar
    podar, processados = processar(PEND, receipts)
    assert podar == []
    assert processados == ["tk2"]


def test_processar_sem_receipt_fica_pendente():
    receipts = {}  # nenhum receipt ainda
    from scripts.verificar_receipts import processar
    podar, processados = processar(PEND, receipts)
    assert podar == []
    assert processados == []


def test_processar_erro_transitorio_nao_poda_mas_processa():
    receipts = {"tk3": {"status": "error", "details": {"error": "MessageRateExceeded"}}}
    from scripts.verificar_receipts import processar
    podar, processados = processar(PEND, receipts)
    assert podar == []
    assert processados == ["tk3"]


def test_presenca_registra_tickets_pendentes():
    tickets = [{"id": "tk1", "token": "ExponentPushToken[a]"}]
    with patch("services.notificacoes.obter_push_token_por_usuario",
               return_value={"expo_token": "ExponentPushToken[a]"}), \
         patch("services.notificacoes.send_expo_push",
               return_value={"ok": ["ExponentPushToken[a]"], "dead": [], "tickets": tickets}), \
         patch("services.notificacoes.remover_push_token"), \
         patch("services.notificacoes.registrar_tickets_pendentes") as reg, \
         patch("services.notificacoes.send_email_resend"):
        from services.notificacoes import enviar_notificacoes_presenca
        enviar_notificacoes_presenca("u1", "Ana", "", "Turma X")
    reg.assert_called_once_with(tickets)


def test_notificar_alunos_registra_tickets_pendentes():
    tickets = [{"id": "tk1", "token": "ExponentPushToken[a]"}]
    alunos = [{"usuario_id": "u1", "expo_token": "ExponentPushToken[a]"}]
    with patch("services.notificacoes.obter_turma_id_por_chamada", return_value="t1"), \
         patch("services.notificacoes.listar_alunos_com_push_token_da_turma", return_value=alunos), \
         patch("services.notificacoes.send_expo_push",
               return_value={"ok": ["ExponentPushToken[a]"], "dead": [], "tickets": tickets}), \
         patch("services.notificacoes.remover_push_token"), \
         patch("services.notificacoes.registrar_tickets_pendentes") as reg:
        from services.notificacoes import notificar_alunos_presentes
        notificar_alunos_presentes("c1", "Turma X")
    reg.assert_called_once_with(tickets)
