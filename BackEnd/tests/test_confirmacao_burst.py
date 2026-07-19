"""Testes da decisão de burst (liveness passivo) — sem AWS/câmera.

Contrato atual (spec 2026-07-19): TEXTURA (MAX no burst) é o gate de vida;
consenso é incondicional (anti-ruído); pose/magnitude é ADVISORY (não decide).
"""
import pytest

from scripts.confirmacao_burst import ConfirmadorBurst, Decisao, ResultadoFrame, Avaliacao


def _conf(min_matches=3, pose_std_min=3.0, texture_min=0.2):
    return ConfirmadorBurst(min_matches=min_matches, pose_std_min=pose_std_min,
                            texture_min=texture_min)


def _frames(eid, specs):
    """specs: lista de (yaw, pitch, textura)."""
    return [ResultadoFrame(external_id=eid, yaw=y, pitch=p, textura=t)
            for y, p, t in specs]


# ---- Consenso (camada 1, incondicional) ----

def test_consenso_insuficiente_descarta():
    r = _frames("a", [(0, 0, 0.9), (1, 1, 0.9)])  # 2 matches < min 3
    assert _conf().avaliar(r) == {"a": Decisao.DESCARTAR}


def test_consenso_insuficiente_descarta_mesmo_com_textura_alta():
    # Precedência: sem consenso, DESCARTAR — textura ótima não resgata.
    r = _frames("a", [(0, 0, 0.99), (5, 5, 0.99)])  # 2 < 3
    assert _conf().avaliar(r) == {"a": Decisao.DESCARTAR}


# ---- Textura (camada 2, gate de vida) ----

def test_consenso_ok_textura_alta_registra():
    r = _frames("a", [(0, 0, 0.8), (0, 0, 0.9), (0, 0, 0.99)])
    assert _conf().avaliar(r) == {"a": Decisao.REGISTRAR}


def test_consenso_ok_textura_baixa_fica_pendente():
    # Foto: textura satura baixo em todos os frames.
    r = _frames("a", [(0, 0, 0.0), (0, 0, 0.001), (0, 0, 0.0)])
    assert _conf().avaliar(r) == {"a": Decisao.PENDENTE}


def test_agrega_textura_por_max_um_frame_bom_salva():
    # Rosto real varia entre frames; MAX defende de frame ruim (0.05).
    r = _frames("a", [(0, 0, 0.05), (0, 0, 0.10), (0, 0, 0.986)])
    assert _conf().avaliar(r) == {"a": Decisao.REGISTRAR}


def test_todos_frames_abaixo_do_limiar_fica_pendente():
    # MAX=0.19 < 0.20 => PENDENTE (nenhum frame prova vida).
    r = _frames("a", [(0, 0, 0.10), (0, 0, 0.19), (0, 0, 0.15)])
    assert _conf().avaliar(r) == {"a": Decisao.PENDENTE}


def test_sem_textura_em_nenhum_frame_fica_pendente_failclosed():
    r = _frames("a", [(0, 0, None), (0, 0, None), (0, 0, None)])
    assert _conf().avaliar(r) == {"a": Decisao.PENDENTE}


def test_limiar_no_exato_registra():
    r = _frames("a", [(0, 0, 0.20), (0, 0, 0.20), (0, 0, 0.20)])
    assert _conf(texture_min=0.20).avaliar(r) == {"a": Decisao.REGISTRAR}


# ---- Pose é ADVISORY: não decide em nenhum sentido ----

def test_pose_rigida_mas_textura_alta_registra():
    # Aluno parado (pose rígida) com textura viva => REGISTRAR (antes era PENDENTE).
    r = _frames("a", [(1.0, 2.0, 0.9), (1.1, 2.0, 0.9), (0.9, 2.1, 0.9)])
    assert _conf().avaliar(r) == {"a": Decisao.REGISTRAR}


def test_pose_muito_variada_mas_textura_baixa_fica_pendente():
    # Foto balançada (pose varia muito) mas textura baixa => PENDENTE. Furo fechado.
    r = _frames("a", [(0, 0, 0.0), (20, 15, 0.01), (40, 30, 0.0)])
    assert _conf().avaliar(r) == {"a": Decisao.PENDENTE}


# ---- Múltiplos alunos, decisões independentes ----

def test_multiplos_alunos():
    r = (
        _frames("vivo", [(0, 0, 0.3), (0, 0, 0.8), (0, 0, 0.95)])
        + _frames("foto", [(0, 0, 0.0), (10, 5, 0.0), (0, 0, 0.01)])
        + _frames("de_passagem", [(0, 0, 0.9)])
    )
    assert _conf().avaliar(r) == {
        "vivo": Decisao.REGISTRAR,
        "foto": Decisao.PENDENTE,
        "de_passagem": Decisao.DESCARTAR,
    }


def test_burst_vazio_retorna_vazio():
    assert _conf().avaliar([]) == {}


# ---- Validação de parâmetros ----

def test_parametros_invalidos():
    with pytest.raises(ValueError):
        ConfirmadorBurst(min_matches=0, pose_std_min=3.0, texture_min=0.2)
    with pytest.raises(ValueError):
        ConfirmadorBurst(min_matches=3, pose_std_min=-1.0, texture_min=0.2)
    with pytest.raises(ValueError):
        ConfirmadorBurst(min_matches=3, pose_std_min=3.0, texture_min=1.5)
    with pytest.raises(ValueError):
        ConfirmadorBurst(min_matches=3, pose_std_min=3.0, texture_min=-0.1)


# ---- Métricas expostas (log/calibração) ----

def test_avaliar_detalhado_expoe_texture_e_pose():
    r = _frames("a", [(0.0, 1.0, 0.3), (5.0, 1.0, 0.9), (10.0, 1.0, 0.5)])
    det = _conf().avaliar_detalhado(r)["a"]
    assert isinstance(det, Avaliacao)
    assert det.decisao == Decisao.REGISTRAR
    assert det.matches == 3
    assert det.texture_max == 0.9
    assert det.std_yaw == pytest.approx(4.0824, abs=1e-3)
    assert det.std_pitch == 0.0
    assert det.magnitude == pytest.approx(4.0824, abs=1e-3)  # advisory


def test_texture_max_none_sem_scores():
    r = _frames("a", [(0, 0, None), (0, 0, None), (0, 0, None)])
    assert _conf().avaliar_detalhado(r)["a"].texture_max is None


def test_magnitude_none_sem_pose():
    r = [ResultadoFrame("a", None, None, 0.9) for _ in range(3)]
    assert _conf().avaliar_detalhado(r)["a"].magnitude is None


def test_avaliar_continua_devolvendo_so_decisoes():
    r = _frames("a", [(0, 0, 0.9), (0, 0, 0.9), (0, 0, 0.9)])
    assert _conf().avaliar(r) == {"a": Decisao.REGISTRAR}


# ---- Gate="pose": fallback paliativo (ENABLE_TEXTURE=off) ----

def _conf_pose(min_matches=3, pose_std_min=3.0):
    return ConfirmadorBurst(min_matches=min_matches, pose_std_min=pose_std_min,
                            texture_min=0.2, gate="pose")


def test_gate_pose_magnitude_alta_registra_ignora_textura():
    # No modo pose, textura é ignorada; magnitude hypot decide.
    r = _frames("a", [(0, 0, 0.0), (5, 5, 0.0), (10, 10, 0.0)])  # textura 0, pose alta
    assert _conf_pose().avaliar(r) == {"a": Decisao.REGISTRAR}


def test_gate_pose_magnitude_baixa_fica_pendente():
    r = _frames("a", [(1.0, 2.0, 0.99), (1.1, 2.0, 0.99), (0.9, 2.1, 0.99)])  # pose rígida
    assert _conf_pose().avaliar(r) == {"a": Decisao.PENDENTE}


def test_gate_invalido():
    with pytest.raises(ValueError):
        ConfirmadorBurst(min_matches=3, pose_std_min=3.0, texture_min=0.2, gate="xyz")
