"""Testes da decisão de burst (liveness passivo) — sem AWS/câmera."""
import pytest

from scripts.confirmacao_burst import ConfirmadorBurst, Decisao, ResultadoFrame


def _conf(min_matches=3, pose_std_min=2.0):
    return ConfirmadorBurst(min_matches=min_matches, pose_std_min=pose_std_min)


def _frames(eid, poses):
    """poses: lista de (yaw, pitch)."""
    return [ResultadoFrame(external_id=eid, yaw=y, pitch=p) for y, p in poses]


def test_consenso_insuficiente_descarta():
    r = _frames("aluno_a", [(0, 0), (1, 1)])  # 2 matches < min 3
    assert _conf().avaliar(r) == {"aluno_a": Decisao.DESCARTAR}


def test_consenso_com_pose_variada_registra():
    # yaw varia 0..10 -> pstdev >> 2.0
    r = _frames("aluno_a", [(0, 0), (5, 0), (10, 0)])
    assert _conf().avaliar(r) == {"aluno_a": Decisao.REGISTRAR}


def test_consenso_com_pose_rigida_fica_pendente():
    # foto plana: yaw/pitch praticamente constantes
    r = _frames("aluno_a", [(1.0, 2.0), (1.1, 2.0), (0.9, 2.1)])
    assert _conf().avaliar(r) == {"aluno_a": Decisao.PENDENTE}


def test_pitch_sozinho_tambem_prova_vida():
    r = _frames("aluno_a", [(0, 0), (0, 5), (0, 10)])
    assert _conf().avaliar(r) == {"aluno_a": Decisao.REGISTRAR}


def test_sem_dados_de_pose_fica_pendente():
    r = [ResultadoFrame("aluno_a", None, None) for _ in range(3)]
    assert _conf().avaliar(r) == {"aluno_a": Decisao.PENDENTE}


def test_uma_unica_amostra_de_pose_fica_pendente():
    r = [
        ResultadoFrame("aluno_a", 5.0, 3.0),
        ResultadoFrame("aluno_a", None, None),
        ResultadoFrame("aluno_a", None, None),
    ]
    assert _conf().avaliar(r) == {"aluno_a": Decisao.PENDENTE}


def test_multiplos_alunos_decisoes_independentes():
    r = (
        _frames("vivo", [(0, 0), (4, 1), (8, 2)])
        + _frames("foto", [(1, 1), (1, 1), (1, 1)])
        + _frames("de_passagem", [(0, 0)])
    )
    assert _conf().avaliar(r) == {
        "vivo": Decisao.REGISTRAR,
        "foto": Decisao.PENDENTE,
        "de_passagem": Decisao.DESCARTAR,
    }


def test_burst_vazio_retorna_vazio():
    assert _conf().avaliar([]) == {}


def test_parametros_invalidos():
    with pytest.raises(ValueError):
        ConfirmadorBurst(min_matches=0, pose_std_min=2.0)
    with pytest.raises(ValueError):
        ConfirmadorBurst(min_matches=3, pose_std_min=-1.0)


def test_sem_dados_de_pose_nao_registra_nem_com_limiar_zero():
    # Fail-safe: limiar 0.0 é config legal, mas sem amostras não há prova de vida.
    conf = ConfirmadorBurst(min_matches=1, pose_std_min=0.0)
    r = [ResultadoFrame("aluno_a", None, None)]
    assert conf.avaliar(r) == {"aluno_a": Decisao.PENDENTE}


def test_duas_amostras_identicas_com_limiar_positivo_fica_pendente():
    # Variância zero MEDIDA (dados reais) contra limiar > 0 => foto/rígido.
    r = _frames("aluno_a", [(3.0, 1.0), (3.0, 1.0), (3.0, 1.0)])
    assert _conf().avaliar(r) == {"aluno_a": Decisao.PENDENTE}


def test_eixos_assimetricos_yaw_num_frame_pitch_no_outro():
    # yaw só em 2 frames (varia 6 > 2.0), pitch só em 1 => yaw sozinho decide.
    r = [
        ResultadoFrame("aluno_a", yaw=0.0, pitch=None),
        ResultadoFrame("aluno_a", yaw=6.0, pitch=None),
        ResultadoFrame("aluno_a", yaw=None, pitch=2.0),
    ]
    assert _conf().avaliar(r) == {"aluno_a": Decisao.REGISTRAR}


def test_consenso_insuficiente_descarta_mesmo_com_pose_muito_variada():
    # Precedência: sem consenso, DESCARTAR — pose ampla não resgata.
    r = _frames("aluno_a", [(0, 0), (50, 40)])  # 2 matches < min 3
    assert _conf().avaliar(r) == {"aluno_a": Decisao.DESCARTAR}


def test_avaliar_detalhado_expoe_metricas():
    from scripts.confirmacao_burst import Avaliacao

    r = _frames("aluno_a", [(0.0, 1.0), (5.0, 1.0), (10.0, 1.0)])
    detalhe = _conf().avaliar_detalhado(r)["aluno_a"]
    assert isinstance(detalhe, Avaliacao)
    assert detalhe.decisao == Decisao.REGISTRAR
    assert detalhe.matches == 3
    assert detalhe.std_yaw == pytest.approx(4.0824, abs=1e-3)
    assert detalhe.std_pitch == 0.0
    # magnitude = hypot(std_yaw, std_pitch); pitch constante => = std_yaw.
    assert detalhe.magnitude == pytest.approx(4.0824, abs=1e-3)


def test_magnitude_none_sem_pose():
    r = [ResultadoFrame("aluno_a", None, None) for _ in range(3)]
    assert _conf().avaliar_detalhado(r)["aluno_a"].magnitude is None


# --- Magnitude combinada (hypot) — paliativo anti-foto 2026-07-18 ---
# Assinatura de foto: variação concentrada num eixo. Rosto vivo: nos dois.
# hypot acumula os eixos, então dá pra SUBIR o limiar barrando a foto de
# um-eixo sem perder o rosto-vivo de dois-eixos (que OR barraria no mesmo limiar).

def test_foto_um_eixo_forte_barra_no_limiar_alto():
    # std_yaw=2.5, std_pitch=0 => hypot=2.5 < 3.0 => PENDENTE (foto tombada).
    r = _frames("foto", [(0.0, 0.0), (5.0, 0.0)])
    av = _conf(min_matches=2, pose_std_min=3.0).avaliar_detalhado(r)["foto"]
    assert av.magnitude == pytest.approx(2.5, abs=1e-6)
    assert av.decisao == Decisao.PENDENTE


def test_rosto_vivo_dois_eixos_registra_no_limiar_alto():
    # std_yaw=2.5 E std_pitch=2.5 => hypot=3.54 >= 3.0 => REGISTRAR (rosto vivo).
    # OR por-eixo no MESMO limiar 3.0 barraria (2.5 < 3.0): é o resgate do hypot.
    r = _frames("vivo", [(0.0, 0.0), (5.0, 5.0)])
    av = _conf(min_matches=2, pose_std_min=3.0).avaliar_detalhado(r)["vivo"]
    assert av.magnitude == pytest.approx(3.5355, abs=1e-3)
    assert av.decisao == Decisao.REGISTRAR


def test_avaliar_continua_devolvendo_so_decisoes():
    r = _frames("aluno_a", [(0, 0), (5, 0), (10, 0)])
    assert _conf().avaliar(r) == {"aluno_a": Decisao.REGISTRAR}
