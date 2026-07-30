"""Estado do consentimento para o card do perfil (sem DB)."""
import datetime

from core.config import POLITICA_PRIVACIDADE_VERSAO
from routers.alunos import consentimento_estado


def _preparar(monkeypatch, ultimo, angulos=("frontal",)):
    monkeypatch.setattr("routers.alunos.buscar_aluno_por_usuario_id",
                        lambda _: {"aluno_id": "aluno-1"})
    monkeypatch.setattr("routers.alunos.obter_ultimo_evento", lambda _: ultimo)
    monkeypatch.setattr("routers.alunos.listar_rostos_ativos_por_aluno",
                        lambda _: [{"angulo": a} for a in angulos])


def test_estado_ativo(monkeypatch):
    _preparar(monkeypatch, {"evento": "aceite", "politica_versao": "1.0",
                            "registrado_em": datetime.datetime(2026, 3, 12, 14, 22, 1)},
              angulos=("frontal", "esquerda"))
    resp = consentimento_estado("u1", current_user={"sub": "u1", "role": "Aluno"})
    assert resp["estado"] == "ativo"
    assert resp["politica_versao"] == "1.0"
    assert resp["registrado_em"] == "2026-03-12T14:22:01"
    assert resp["angulos_cadastrados"] == ["frontal", "esquerda"]


def test_estado_revogado(monkeypatch):
    _preparar(monkeypatch, {"evento": "revogacao", "politica_versao": "1.0",
                            "registrado_em": datetime.datetime(2026, 5, 1, 9, 0, 0)},
              angulos=())
    resp = consentimento_estado("u1", current_user={"sub": "u1", "role": "Aluno"})
    assert resp["estado"] == "revogado"
    assert resp["angulos_cadastrados"] == []


def test_estado_nunca(monkeypatch):
    _preparar(monkeypatch, None, angulos=())
    resp = consentimento_estado("u1", current_user={"sub": "u1", "role": "Aluno"})
    assert resp["estado"] == "nunca"
    assert resp["politica_versao"] is None
    assert resp["registrado_em"] is None
    assert resp["angulos_cadastrados"] == []


def test_estado_legado_preserva_marcador(monkeypatch):
    # O app renderiza 'legado' como "anterior ao versionamento" — não pode virar "1.0".
    _preparar(monkeypatch, {"evento": "aceite", "politica_versao": "legado",
                            "registrado_em": datetime.datetime(2026, 1, 5, 8, 0, 0)})
    resp = consentimento_estado("u1", current_user={"sub": "u1", "role": "Aluno"})
    assert resp["politica_versao"] == "legado"
    assert resp["estado"] == "ativo"


def test_devolve_politica_vigente(monkeypatch):
    _preparar(monkeypatch, None, angulos=())
    resp = consentimento_estado("u1", current_user={"sub": "u1", "role": "Aluno"})
    assert resp["politica_vigente"]["versao"] == POLITICA_PRIVACIDADE_VERSAO
    assert "url" in resp["politica_vigente"]
