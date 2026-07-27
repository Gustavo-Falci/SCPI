"""O fechamento automático só notifica quem realmente fechou a chamada.

Com gunicorn -w 4 os quatro workers rodam o agendador ao mesmo tempo. O UPDATE
guardado por status='Aberta' é o claim: quem perde a corrida afeta 0 linhas e
não pode devolver a chamada para o agendador notificar.
"""
import datetime
from unittest.mock import MagicMock, PropertyMock, patch

# quarta-feira 10:00 — weekday() e time() são os únicos campos usados na query
AGORA = datetime.datetime(2026, 7, 29, 10, 0)


def _linha(chamada_id):
    return {
        "chamada_id": chamada_id,
        "turma_id": "turma-1",
        "nome_disciplina": "Banco de Dados",
    }


def _mock_cursor(rows):
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return cm, cur


def test_nao_devolve_chamada_quando_update_nao_afetou_linha():
    cm, cur = _mock_cursor([_linha("c1")])
    cur.rowcount = 0  # outro worker fechou primeiro

    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import fechar_chamadas_expiradas
        fechadas = fechar_chamadas_expiradas(agora=AGORA)

    assert fechadas == []


def test_devolve_chamada_quando_update_afetou_linha():
    cm, cur = _mock_cursor([_linha("c1")])
    cur.rowcount = 1  # este worker ganhou o claim

    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import fechar_chamadas_expiradas
        fechadas = fechar_chamadas_expiradas(agora=AGORA)

    assert [f["chamada_id"] for f in fechadas] == ["c1"]


def test_devolve_apenas_as_linhas_reivindicadas():
    cm, cur = _mock_cursor([_linha("c1"), _linha("c2")])
    # rowcount é lido uma vez por UPDATE, na ordem das linhas
    type(cur).rowcount = PropertyMock(side_effect=[1, 0])

    with patch("repositories.chamadas.get_db_cursor", return_value=cm):
        from repositories.chamadas import fechar_chamadas_expiradas
        fechadas = fechar_chamadas_expiradas(agora=AGORA)

    assert [f["chamada_id"] for f in fechadas] == ["c1"]
