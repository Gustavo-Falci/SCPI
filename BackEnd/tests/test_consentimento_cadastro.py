"""Validação de consentimento no cadastro de face (sem DB nem AWS)."""
import pytest
from fastapi import HTTPException

from core.config import POLITICA_PRIVACIDADE_VERSAO
from core.errors import ErrorCode
from routers.alunos import registrar_aceite_se_novo, validar_consentimento


def test_consentimento_false_rejeita():
    with pytest.raises(HTTPException) as exc:
        validar_consentimento(False, POLITICA_PRIVACIDADE_VERSAO)
    assert exc.value.status_code == 400
    assert exc.value.detail["error_code"] == ErrorCode.CONSENTIMENTO_OBRIGATORIO


def test_politica_desatualizada_rejeita():
    with pytest.raises(HTTPException) as exc:
        validar_consentimento(True, "0.9")
    assert exc.value.status_code == 400
    assert exc.value.detail["error_code"] == ErrorCode.POLITICA_DESATUALIZADA


def test_versao_vigente_com_consentimento_passa():
    assert validar_consentimento(True, POLITICA_PRIVACIDADE_VERSAO) is None


def test_consentimento_false_tem_precedencia_sobre_versao():
    # Sem consentimento a versão nem importa — a mensagem certa é a do aceite.
    with pytest.raises(HTTPException) as exc:
        validar_consentimento(False, "0.9")
    assert exc.value.detail["error_code"] == ErrorCode.CONSENTIMENTO_OBRIGATORIO


def test_primeiro_angulo_registra_aceite(monkeypatch):
    chamadas = []
    monkeypatch.setattr("routers.alunos.obter_ultimo_evento", lambda _: None)
    monkeypatch.setattr("routers.alunos.registrar_evento",
                        lambda *a, **k: chamadas.append((a, k)) or True)

    registrar_aceite_se_novo("aluno-1", "1.0", ip="203.0.113.7", user_agent="Expo")

    assert len(chamadas) == 1
    assert chamadas[0][0][1] == "aceite"


def test_angulos_seguintes_nao_duplicam_aceite(monkeypatch):
    chamadas = []
    monkeypatch.setattr("routers.alunos.obter_ultimo_evento",
                        lambda _: {"evento": "aceite", "politica_versao": "1.0"})
    monkeypatch.setattr("routers.alunos.registrar_evento",
                        lambda *a, **k: chamadas.append(a) or True)

    registrar_aceite_se_novo("aluno-1", "1.0", ip=None, user_agent=None)

    assert chamadas == []


def test_aceite_apos_revogacao_gera_evento_novo(monkeypatch):
    chamadas = []
    monkeypatch.setattr("routers.alunos.obter_ultimo_evento",
                        lambda _: {"evento": "revogacao", "politica_versao": "1.0"})
    monkeypatch.setattr("routers.alunos.registrar_evento",
                        lambda *a, **k: chamadas.append(a) or True)

    registrar_aceite_se_novo("aluno-1", "1.0", ip=None, user_agent=None)

    assert len(chamadas) == 1


def test_aceite_legado_e_substituido_por_versao_vigente(monkeypatch):
    # Aluno do backfill: precisa gerar aceite versionado ao recadastrar.
    chamadas = []
    monkeypatch.setattr("routers.alunos.obter_ultimo_evento",
                        lambda _: {"evento": "aceite", "politica_versao": "legado"})
    monkeypatch.setattr("routers.alunos.registrar_evento",
                        lambda *a, **k: chamadas.append(a) or True)

    registrar_aceite_se_novo("aluno-1", "1.0", ip=None, user_agent=None)

    assert len(chamadas) == 1
