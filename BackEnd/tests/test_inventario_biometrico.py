"""Reconciliação do inventário biométrico — função pura, sem AWS e sem banco."""
import pytest

from services.inventario_biometrico import reconciliar_inventario


def face(face_id, nome="ana"):
    return {"face_id": face_id, "external_image_id": nome, "image_id": f"img-{face_id}"}


def objeto(key, size=1000):
    return {"key": key, "size": size, "last_modified": "2026-07-01T12:00:00"}


def registro(face_id=None, path=None, angulo="frontal", revogado=None,
             aluno_id="a1", nome="Ana Souza", ra="2024001"):
    return {
        "face_id_rekognition": face_id, "s3_path_cadastro": path, "angulo": angulo,
        "revogado_em": revogado, "aluno_id": aluno_id, "nome": nome, "ra": ra,
    }


def test_face_sem_registro_e_orfa():
    res = reconciliar_inventario([face("f1")], [], [])
    item = res["rekognition"][0]
    assert item["status"] == "orfao"
    assert item["aluno"] is None
    assert item["angulo"] is None


def test_face_orfa_nao_e_marcada_divergente():
    """Órfão já é o diagnóstico mais forte; somar rótulos só polui a leitura."""
    res = reconciliar_inventario([face("f1")], [], [])
    assert res["rekognition"][0]["divergente"] is False


def test_face_com_registro_ativo_e_foto_esta_ok():
    res = reconciliar_inventario(
        [face("f1")], [objeto("alunos/a.jpg")],
        [registro(face_id="f1", path="alunos/a.jpg")],
    )
    item = res["rekognition"][0]
    assert item["status"] == "ok"
    assert item["divergente"] is False
    assert item["aluno"] == {"aluno_id": "a1", "nome": "Ana Souza", "ra": "2024001"}
    assert item["angulo"] == "frontal"


def test_face_de_registro_revogado_continua_na_collection():
    res = reconciliar_inventario(
        [face("f1")], [objeto("alunos/a.jpg")],
        [registro(face_id="f1", path="alunos/a.jpg", revogado="2026-07-01")],
    )
    assert res["rekognition"][0]["status"] == "revogado"


def test_face_sem_path_no_registro_e_divergente():
    res = reconciliar_inventario([face("f1")], [], [registro(face_id="f1", path=None)])
    assert res["rekognition"][0]["divergente"] is True


def test_face_cujo_arquivo_sumiu_do_bucket_e_divergente():
    res = reconciliar_inventario(
        [face("f1")], [objeto("alunos/outro.jpg")],
        [registro(face_id="f1", path="alunos/a.jpg")],
    )
    assert res["rekognition"][0]["divergente"] is True


def test_objeto_sem_registro_e_orfao():
    res = reconciliar_inventario([], [objeto("alunos/solto.jpg")], [])
    item = res["s3"][0]
    assert item["status"] == "orfao"
    assert item["aluno"] is None


def test_objeto_de_registro_revogado():
    res = reconciliar_inventario(
        [], [objeto("alunos/a.jpg")],
        [registro(face_id="f1", path="alunos/a.jpg", revogado="2026-07-01")],
    )
    assert res["s3"][0]["status"] == "revogado"


def test_objeto_sem_face_indexada_e_divergente():
    res = reconciliar_inventario(
        [], [objeto("alunos/a.jpg")], [registro(face_id="f1", path="alunos/a.jpg")],
    )
    assert res["s3"][0]["divergente"] is True


def test_objeto_preserva_size_e_last_modified():
    res = reconciliar_inventario([], [objeto("alunos/a.jpg", size=8421)], [])
    assert res["s3"][0]["size"] == 8421
    assert res["s3"][0]["last_modified"] == "2026-07-01T12:00:00"


def test_aluno_com_tres_de_quatro_angulos_e_incompleto():
    registros = [
        registro(face_id="f1", path="alunos/1.jpg", angulo="frontal"),
        registro(face_id="f2", path="alunos/2.jpg", angulo="esquerda"),
        registro(face_id="f3", path="alunos/3.jpg", angulo="direita"),
    ]
    res = reconciliar_inventario([], [], registros)
    aluno = res["alunos"][0]
    assert aluno["incompleto"] is True
    assert aluno["angulos_faltantes"] == ["baixo"]
    assert aluno["angulos_presentes"] == ["direita", "esquerda", "frontal"]


def test_aluno_com_os_quatro_angulos_esta_completo():
    registros = [
        registro(face_id=f"f{i}", path=f"alunos/{i}.jpg", angulo=ang)
        for i, ang in enumerate(["frontal", "esquerda", "direita", "baixo"])
    ]
    res = reconciliar_inventario([], [], registros)
    assert res["alunos"][0]["incompleto"] is False
    assert res["alunos"][0]["angulos_faltantes"] == []


def test_angulo_revogado_nao_conta_como_presente():
    """Revogar um ângulo devolve o aluno à condição de incompleto."""
    registros = [
        registro(face_id="f1", path="alunos/1.jpg", angulo="frontal"),
        registro(face_id="f2", path="alunos/2.jpg", angulo="esquerda", revogado="2026-07-01"),
    ]
    res = reconciliar_inventario([], [], registros)
    assert res["alunos"][0]["angulos_presentes"] == ["frontal"]
    assert "esquerda" in res["alunos"][0]["angulos_faltantes"]


def test_aluno_so_com_registros_revogados_nao_aparece():
    registros = [registro(face_id="f1", path="alunos/1.jpg", revogado="2026-07-01")]
    res = reconciliar_inventario([], [], registros)
    assert res["alunos"] == []


def test_dois_alunos_sao_agrupados_separadamente():
    registros = [
        registro(face_id="f1", path="alunos/1.jpg", aluno_id="a1", nome="Ana Souza"),
        registro(face_id="f2", path="alunos/2.jpg", aluno_id="a2", nome="Bruno Lima"),
    ]
    res = reconciliar_inventario([], [], registros)
    assert sorted(a["nome"] for a in res["alunos"]) == ["Ana Souza", "Bruno Lima"]


def test_resumo_conta_cada_categoria():
    faces = [face("f1"), face("f2"), face("f3")]
    objetos = [objeto("alunos/a.jpg"), objeto("alunos/solto.jpg")]
    registros = [
        registro(face_id="f1", path="alunos/a.jpg"),                      # ok
        registro(face_id="f2", path="alunos/sumiu.jpg", revogado="2026-07-01"),
        # f3 não tem registro → órfã
    ]
    res = reconciliar_inventario(faces, objetos, registros)
    assert res["resumo"]["rekognition"] == {
        "total": 3, "orfaos": 1, "revogados": 1, "divergentes": 1,
    }
    assert res["resumo"]["s3"]["total"] == 2
    assert res["resumo"]["s3"]["orfaos"] == 1


def test_resumo_conta_alunos_incompletos():
    registros = [
        registro(face_id="f1", path="alunos/1.jpg", aluno_id="a1", angulo="frontal"),
        registro(face_id="f2", path="alunos/2.jpg", aluno_id="a2", angulo="frontal"),
    ]
    res = reconciliar_inventario([], [], registros)
    assert res["resumo"]["alunos_incompletos"] == 2


def test_inventario_vazio():
    res = reconciliar_inventario([], [], [])
    assert res["rekognition"] == [] and res["s3"] == [] and res["alunos"] == []
    assert res["resumo"]["alunos_incompletos"] == 0
    assert res["indisponivel"] == []


@pytest.mark.parametrize("lado", ["rekognition", "s3"])
def test_lado_indisponivel_suspende_divergencia(lado):
    """Sem os dois lados, tudo pareceria divergente — acusação falsa em massa."""
    res = reconciliar_inventario(
        [face("f1")], [], [registro(face_id="f1", path="alunos/a.jpg")],
        indisponivel=[lado],
    )
    assert res["indisponivel"] == [lado]
    assert all(not i["divergente"] for i in res["rekognition"])
    assert all(not i["divergente"] for i in res["s3"])


def test_status_continua_valendo_com_lado_indisponivel():
    """Órfão e revogado dependem só do banco, então seguem confiáveis."""
    res = reconciliar_inventario([face("f1")], [], [], indisponivel=["s3"])
    assert res["rekognition"][0]["status"] == "orfao"
