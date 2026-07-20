"""Testes da importação em massa de alunos (repo + service) — sem DB real."""
from unittest.mock import MagicMock, patch


def _mock_cursor(fetchone_side_effect=None, fetchall_return=None):
    """Retorna (context_manager, cursor) para patchar get_db_cursor."""
    cur = MagicMock()
    if fetchone_side_effect is not None:
        cur.fetchone.side_effect = fetchone_side_effect
    cur.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return cm, cur


def test_importar_aluno_csv_sem_turma_nao_matricula():
    # fetchone: 1) INSERT Usuarios RETURNING  2) INSERT Alunos RETURNING
    cm, cur = _mock_cursor(fetchone_side_effect=[{"usuario_id": "u1"}, {"aluno_id": "a1"}])
    with patch("repositories.alunos.get_db_cursor", return_value=cm):
        from repositories.alunos import importar_aluno_csv
        novo, email, matriculado = importar_aluno_csv(
            None, "Maria Santos", "maria@escola.com", "2024001", "Matutino", "hash"
        )
    assert novo is True
    assert email == "maria@escola.com"
    assert matriculado is False
    sqls = " ".join(call[0][0] for call in cur.execute.call_args_list)
    assert "Turma_Alunos" not in sqls


def test_importar_aluno_csv_com_turma_matricula():
    cm, cur = _mock_cursor(fetchone_side_effect=[{"usuario_id": "u1"}, {"aluno_id": "a1"}])
    with patch("repositories.alunos.get_db_cursor", return_value=cm):
        from repositories.alunos import importar_aluno_csv
        novo, _email, matriculado = importar_aluno_csv(
            "t1", "Maria Santos", "maria@escola.com", "2024001", None, "hash"
        )
    assert novo is True
    assert matriculado is True
    sqls = " ".join(call[0][0] for call in cur.execute.call_args_list)
    assert "Turma_Alunos" in sqls


def test_importar_aluno_csv_usuario_existente_retorna_novo_false():
    # INSERT Usuarios não retorna (ON CONFLICT DO NOTHING) → SELECT acha o usuário
    cm, cur = _mock_cursor(fetchone_side_effect=[
        None, {"usuario_id": "u1"}, {"aluno_id": "a1"},
    ])
    with patch("repositories.alunos.get_db_cursor", return_value=cm):
        from repositories.alunos import importar_aluno_csv
        novo, _email, matriculado = importar_aluno_csv(
            "t1", "Maria Santos", "maria@escola.com", "2024001", None, "hash"
        )
    assert novo is False
    assert matriculado is True


def test_importar_aluno_csv_sem_cursor_retorna_tupla():
    cm = MagicMock()
    cm.__enter__.return_value = None
    cm.__exit__.return_value = False
    with patch("repositories.alunos.get_db_cursor", return_value=cm):
        from repositories.alunos import importar_aluno_csv
        assert importar_aluno_csv(None, "Maria", "m@e.com", "2024001", None, "h") == (False, None, False)


def test_mapear_codigos_turma_retorna_dict():
    cm, _cur = _mock_cursor(fetchall_return=[
        {"codigo_turma": "MAT-101", "turma_id": "t1"},
        {"codigo_turma": "FIS-202", "turma_id": "t2"},
    ])
    with patch("repositories.turmas.get_db_cursor", return_value=cm):
        from repositories.turmas import mapear_codigos_turma
        assert mapear_codigos_turma() == {"MAT-101": "t1", "FIS-202": "t2"}


def test_mapear_codigos_turma_sem_cursor_retorna_vazio():
    cm = MagicMock()
    cm.__enter__.return_value = None
    cm.__exit__.return_value = False
    with patch("repositories.turmas.get_db_cursor", return_value=cm):
        from repositories.turmas import mapear_codigos_turma
        assert mapear_codigos_turma() == {}


# ---------------------------------------------------------------- service

import pytest
from fastapi import HTTPException

HEADER = "nome,email,ra,turno,turma\n"


def _csv(*linhas):
    return (HEADER + "".join(l + "\n" for l in linhas)).encode("utf-8")


def _patch_service(importar_retorno=(True, "x@e.com", False), turmas=None):
    """Patcha as dependências de processar_csv_alunos. Retorna (patch_importar, patch_mapa)."""
    return (
        patch("services.import_alunos.importar_aluno_csv", return_value=importar_retorno),
        patch("services.import_alunos.mapear_codigos_turma",
              return_value=turmas if turmas is not None else {"MAT-101": "t1"}),
    )


def test_processar_csv_sem_coluna_turma_nao_matricula():
    p_imp, p_mapa = _patch_service(importar_retorno=(True, "maria@escola.com", False))
    with p_imp as imp, p_mapa:
        from services.import_alunos import processar_csv_alunos
        res = processar_csv_alunos(_csv("Maria Santos,maria@escola.com,2024001,Matutino,"))
    assert res.importados == 1
    assert res.matriculados == 0
    assert res.erros == []
    assert imp.call_args[0][0] is None  # turma_id


def test_processar_csv_com_turma_valida_matricula():
    p_imp, p_mapa = _patch_service(importar_retorno=(True, "maria@escola.com", True))
    with p_imp as imp, p_mapa:
        from services.import_alunos import processar_csv_alunos
        res = processar_csv_alunos(_csv("Maria Santos,maria@escola.com,2024001,,MAT-101"))
    assert res.importados == 1
    assert res.matriculados == 1
    assert imp.call_args[0][0] == "t1"


def test_processar_csv_turma_inexistente_gera_erro_e_nao_grava():
    p_imp, p_mapa = _patch_service()
    with p_imp as imp, p_mapa:
        from services.import_alunos import processar_csv_alunos
        res = processar_csv_alunos(_csv(
            "Maria Santos,maria@escola.com,2024001,,XPTO",
            "Joao Silva,joao@escola.com,2024002,,MAT-101",
        ))
    assert res.erros == ["Linha 2: turma 'XPTO' não encontrada."]
    assert imp.call_count == 1  # só a linha 3 gravou
    assert res.importados == 1


def test_processar_csv_duplicado_conta_sem_email():
    chamadas = []
    p_imp, p_mapa = _patch_service(importar_retorno=(False, "maria@escola.com", True))
    with p_imp, p_mapa:
        from services.import_alunos import processar_csv_alunos
        res = processar_csv_alunos(
            _csv("Maria Santos,maria@escola.com,2024001,,MAT-101"),
            on_novo_usuario=lambda *a: chamadas.append(a),
        )
    assert res.importados == 0
    assert res.duplicados == 1
    assert res.matriculados == 1
    assert res.emails_enviados == 0
    assert chamadas == []


def test_processar_csv_novo_usuario_dispara_callback():
    chamadas = []
    p_imp, p_mapa = _patch_service(importar_retorno=(True, "maria@escola.com", False))
    with p_imp, p_mapa:
        from services.import_alunos import processar_csv_alunos
        res = processar_csv_alunos(
            _csv("Maria Santos,maria@escola.com,2024001,,"),
            on_novo_usuario=lambda email, nome, senha: chamadas.append((email, nome, senha)),
        )
    assert res.emails_enviados == 1
    assert chamadas[0][0] == "maria@escola.com"
    assert chamadas[0][1] == "Maria Santos"
    assert chamadas[0][2]  # senha temporária não vazia


@pytest.mark.parametrize("linha,trecho_erro", [
    ("Ma,maria@escola.com,2024001,,", "3 caracteres"),
    ("Maria Santos,maria-arroba-escola,2024001,,", "E-mail"),
    ("Maria Santos,maria@escola.com,12,,", "RA"),
])
def test_processar_csv_validacoes_de_linha(linha, trecho_erro):
    p_imp, p_mapa = _patch_service()
    with p_imp as imp, p_mapa:
        from services.import_alunos import processar_csv_alunos
        res = processar_csv_alunos(_csv(linha))
    assert len(res.erros) == 1
    assert res.erros[0].startswith("Linha 2: ")
    assert trecho_erro in res.erros[0]
    assert imp.call_count == 0


def test_processar_csv_bloqueia_injection():
    p_imp, p_mapa = _patch_service()
    with p_imp as imp, p_mapa:
        from services.import_alunos import processar_csv_alunos
        res = processar_csv_alunos(_csv("=cmd|calc,maria@escola.com,2024001,,"))
    assert len(res.erros) == 1
    assert "injection" in res.erros[0].lower()
    assert imp.call_count == 0


def test_processar_csv_linha_incompleta_e_ignorada_em_silencio():
    p_imp, p_mapa = _patch_service()
    with p_imp as imp, p_mapa:
        from services.import_alunos import processar_csv_alunos
        res = processar_csv_alunos(_csv(",,,,"))
    assert res.erros == []
    assert res.importados == 0
    assert imp.call_count == 0


def test_processar_csv_turno_invalido_vira_none():
    p_imp, p_mapa = _patch_service()
    with p_imp as imp, p_mapa:
        from services.import_alunos import processar_csv_alunos
        processar_csv_alunos(_csv("Maria Santos,maria@escola.com,2024001,Vespertino,"))
    assert imp.call_args[0][4] is None  # turno


def test_processar_csv_turma_id_fixo_ignora_coluna_turma():
    p_imp, p_mapa = _patch_service()
    with p_imp as imp, p_mapa as mapa:
        from services.import_alunos import processar_csv_alunos
        processar_csv_alunos(
            _csv("Maria Santos,maria@escola.com,2024001,,XPTO"), turma_id_fixo="t9"
        )
    assert imp.call_args[0][0] == "t9"
    mapa.assert_not_called()  # não carrega o mapa quando a turma é fixa


def test_processar_csv_arquivo_grande_413():
    from services.import_alunos import processar_csv_alunos
    from core.csv_utils import MAX_CSV_BYTES
    with pytest.raises(HTTPException) as exc:
        processar_csv_alunos(b"x" * (MAX_CSV_BYTES + 1))
    assert exc.value.status_code == 413


def test_processar_csv_nao_utf8_400():
    from services.import_alunos import processar_csv_alunos
    with pytest.raises(HTTPException) as exc:
        processar_csv_alunos("nome\nMaría".encode("latin-1"))
    assert exc.value.status_code == 400


def test_processar_csv_vazio_400():
    from services.import_alunos import processar_csv_alunos
    with pytest.raises(HTTPException) as exc:
        processar_csv_alunos(b"")
    assert exc.value.status_code == 400


# ---------------------------------------------------------------- rotas

def test_validar_upload_csv_rejeita_extensao():
    from routers.admin import _validar_extensao_csv
    with pytest.raises(HTTPException) as exc:
        _validar_extensao_csv("alunos.xlsx")
    assert exc.value.status_code == 400


def test_validar_upload_csv_aceita_maiusculo():
    from routers.admin import _validar_extensao_csv
    _validar_extensao_csv("ALUNOS.CSV")  # não levanta
