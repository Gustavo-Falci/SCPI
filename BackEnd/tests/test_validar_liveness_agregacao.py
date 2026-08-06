"""Agregação da validação Fase 0 — a conta que define o limiar de textura.

O gate de produção decide por MAX dos scores do burst (confirmacao_burst.
avaliar_detalhado). Logo a estatística que importa é max-por-burst, não
por frame: um único frame de vídeo acima do limiar já registra presença.
"""
import math
import pathlib

from scripts._validar_liveness import _max_por_burst, _meio_geometrico, _separacao, _LABELS, _descobrir_bursts


def test_max_por_burst_pega_o_maior_de_cada_burst():
    assert _max_por_burst([[0.01, 0.40, 0.02], [0.05, 0.06]]) == [0.40, 0.06]


def test_max_por_burst_descarta_burst_vazio():
    # Burst em que nenhum frame teve rosto detectado não vira amostra.
    assert _max_por_burst([[0.3], [], [0.1]]) == [0.3, 0.1]


def test_separacao_usa_pior_real_contra_melhor_fake():
    R, V, folga = _separacao([0.50, 0.20, 0.90], [0.01, 0.05, 0.02])
    assert R == 0.20
    assert V == 0.05
    assert folga == 4.0


def test_separacao_sem_amostra_devolve_none():
    assert _separacao([], [0.01]) == (None, None, None)
    assert _separacao([0.5], []) == (None, None, None)


def test_separacao_com_fake_zerado_nao_divide_por_zero():
    # Caso real: foto satura em 0.000 no frame raw (medição de 2026-07-19).
    R, V, folga = _separacao([0.30], [0.0, 0.0])
    assert R == 0.30
    assert V == 0.0
    assert folga == math.inf


def test_meio_geometrico():
    assert _meio_geometrico(0.32, 0.02) == 0.08


def test_label_de_video_existe_e_e_separado_de_foto_em_tela():
    # 't' = foto em tela (calibração de 2026-07-19), 'v' = vídeo em tela (novo).
    assert _LABELS["t"] == "tela"
    assert _LABELS["v"] == "video"


def _mk_burst(raiz, label, cond, n, n_frames=2):
    d = raiz / label / cond / f"burst_{n:03d}"
    d.mkdir(parents=True)
    for i in range(n_frames):
        (d / f"frame_{i}.jpg").write_bytes(b"x")
        (d / f"frame_{i}.txt").write_text("10 10 80 80")
    return d


def test_descobrir_bursts_agrupa_por_condicao(tmp_path):
    _mk_burst(tmp_path, "video", "2m-celular", 0)
    _mk_burst(tmp_path, "video", "2m-celular", 1)
    _mk_burst(tmp_path, "video", "0.5m-tablet", 0)

    achados = _descobrir_bursts(tmp_path, "video")

    assert [c for c, _ in achados] == ["0.5m-tablet", "2m-celular", "2m-celular"]
    assert all(d.is_dir() for _, d in achados)


def test_descobrir_bursts_ignora_amostra_antiga_de_frame_solto(tmp_path):
    # Layout de 2026-07-19: <label>/real_000.jpg, sem diretório de burst.
    antigo = tmp_path / "real"
    antigo.mkdir(parents=True)
    (antigo / "real_000.jpg").write_bytes(b"x")
    (antigo / "real_000.txt").write_text("10 10 80 80")

    assert _descobrir_bursts(tmp_path, "real") == []


def test_descobrir_bursts_label_inexistente_devolve_vazio(tmp_path):
    assert _descobrir_bursts(tmp_path, "video") == []
