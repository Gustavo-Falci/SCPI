"""_sincronizar_chamada: falha do servidor não pode virar "chamada acabou".

O tracker é o que impede a câmera de re-enviar quem já foi marcado. Um
limpar() indevido custa um SearchFaces por aluno da sala no burst seguinte —
e é o Rekognition que domina o custo por aula.

Os testes montam a instância com __new__: o __init__ real abre modelo YuNet,
detector de textura e exige CAMERA_SERVICE_TOKEN. Só os três atributos que
_sincronizar_chamada toca são preenchidos.
"""
import threading
from unittest.mock import MagicMock

import pytest

from scripts.registro_tracker import RegistroPresencaTracker


@pytest.fixture
def sistema():
    from scripts.reconhecimento_tempo_real import SistemaReconhecimento

    obj = SistemaReconhecimento.__new__(SistemaReconhecimento)
    obj.chamada_id_atual = 7
    obj.tracker = RegistroPresencaTracker()
    obj.lock = threading.Lock()
    # Dois alunos já marcados nesta chamada — é o que não pode se perder.
    obj.tracker.concluir("aluno-a", definitivo=True)
    obj.tracker.concluir("aluno-b", definitivo=True)
    return obj


def _resposta(status, corpo=None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = corpo if corpo is not None else {}
    return resp


def _sincronizar(monkeypatch, sistema, resposta=None, erro=None):
    import scripts.reconhecimento_tempo_real as mod

    def _get(*_a, **_k):
        if erro is not None:
            raise erro
        return resposta

    monkeypatch.setattr(mod.requests, "get", _get)
    sistema._sincronizar_chamada()


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_5xx_preserva_chamada_e_tracker(monkeypatch, sistema, status):
    """O bug: 503 → chamada_id None → limpar() → sala inteira re-POSTada."""
    _sincronizar(monkeypatch, sistema, _resposta(status))

    assert sistema.chamada_id_atual == 7
    assert len(sistema.tracker) == 2
    assert sistema.tracker.tratado("aluno-a")


def test_timeout_preserva_chamada_e_tracker(monkeypatch, sistema):
    """Comportamento que já existia — fixado contra regressão."""
    _sincronizar(monkeypatch, sistema, erro=OSError("timeout"))

    assert sistema.chamada_id_atual == 7
    assert len(sistema.tracker) == 2


def test_chamada_fechada_de_verdade_reseta(monkeypatch, sistema):
    """200 com chamada_id null é resposta, não falha: aí o reset é correto."""
    _sincronizar(monkeypatch, sistema, _resposta(200, {"chamada_id": None}))

    assert sistema.chamada_id_atual is None
    assert len(sistema.tracker) == 0


def test_troca_de_chamada_reseta(monkeypatch, sistema):
    """Aula nova na mesma sala: nada da anterior vale."""
    _sincronizar(monkeypatch, sistema, _resposta(200, {"chamada_id": 9}))

    assert sistema.chamada_id_atual == 9
    assert len(sistema.tracker) == 0


def test_mesma_chamada_nao_mexe_no_tracker(monkeypatch, sistema):
    """O caso comum — roda a cada ciclo, não pode ter efeito nenhum."""
    _sincronizar(monkeypatch, sistema, _resposta(200, {"chamada_id": 7}))

    assert sistema.chamada_id_atual == 7
    assert len(sistema.tracker) == 2


def test_403_reseta(monkeypatch, sistema):
    """Token revogado/inválido é recusa definitiva: não há chamada para manter."""
    _sincronizar(monkeypatch, sistema, _resposta(403))

    assert sistema.chamada_id_atual is None
    assert len(sistema.tracker) == 0
