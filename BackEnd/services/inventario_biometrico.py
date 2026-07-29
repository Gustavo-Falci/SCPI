"""Reconciliação entre AWS e banco para a auditoria da aba Biometria.

Função pura de propósito: recebe as três listas prontas e não conhece boto3 nem
psycopg2. Toda a regra de "isto aqui é lixo" fica testável de mesa, sem AWS.
"""
from core.regras import ANGULOS_VALIDOS


def _aluno_de(reg):
    return {"aluno_id": reg["aluno_id"], "nome": reg["nome"], "ra": reg["ra"]}


def _status_de(reg):
    return "revogado" if reg["revogado_em"] else "ok"


def _montar_alunos(registros_db):
    """Agrupa os registros ATIVOS por aluno e calcula ângulos faltantes.

    Só entra quem tem ao menos um ângulo ativo: aluno sem biometria nenhuma não
    tem linha em Colecao_Rostos e é assunto da aba Alunos, não desta.
    """
    por_aluno = {}
    for reg in registros_db:
        if reg["revogado_em"]:
            continue
        chave = str(reg["aluno_id"])
        alvo = por_aluno.setdefault(chave, {"reg": reg, "angulos": set()})
        if reg["angulo"]:
            alvo["angulos"].add(reg["angulo"])

    alunos = []
    for dados in por_aluno.values():
        faltantes = sorted(ANGULOS_VALIDOS - dados["angulos"])
        alunos.append({
            **_aluno_de(dados["reg"]),
            "angulos_presentes": sorted(dados["angulos"]),
            "angulos_faltantes": faltantes,
            "incompleto": bool(faltantes),
        })
    return alunos


def _contar(itens):
    return {
        "total": len(itens),
        "orfaos": sum(1 for i in itens if i["status"] == "orfao"),
        "revogados": sum(1 for i in itens if i["status"] == "revogado"),
        "divergentes": sum(1 for i in itens if i["divergente"]),
    }


def reconciliar_inventario(faces_aws, objetos_s3, registros_db, indisponivel=()):
    """Cruza collection, bucket e banco, devolvendo o inventário auditado."""
    indisponivel = list(indisponivel)
    # Divergência precisa dos DOIS lados. Com um deles faltando, tudo pareceria
    # sem par e a tela acusaria divergência falsa em massa.
    checar_divergencia = not indisponivel

    por_face = {r["face_id_rekognition"]: r for r in registros_db if r["face_id_rekognition"]}
    por_path = {r["s3_path_cadastro"]: r for r in registros_db if r["s3_path_cadastro"]}
    keys_s3 = {o["key"] for o in objetos_s3}
    face_ids = {f["face_id"] for f in faces_aws}

    rekognition = []
    for f in faces_aws:
        reg = por_face.get(f["face_id"])
        if reg is None:
            rekognition.append({**f, "status": "orfao", "divergente": False,
                                "aluno": None, "angulo": None})
            continue
        sem_par = not reg["s3_path_cadastro"] or reg["s3_path_cadastro"] not in keys_s3
        rekognition.append({
            **f,
            "status": _status_de(reg),
            "divergente": bool(checar_divergencia and sem_par),
            "aluno": _aluno_de(reg),
            "angulo": reg["angulo"],
        })

    s3 = []
    for o in objetos_s3:
        reg = por_path.get(o["key"])
        if reg is None:
            s3.append({**o, "status": "orfao", "divergente": False,
                       "aluno": None, "angulo": None})
            continue
        sem_par = not reg["face_id_rekognition"] or reg["face_id_rekognition"] not in face_ids
        s3.append({
            **o,
            "status": _status_de(reg),
            "divergente": bool(checar_divergencia and sem_par),
            "aluno": _aluno_de(reg),
            "angulo": reg["angulo"],
        })

    alunos = _montar_alunos(registros_db)

    return {
        "rekognition": rekognition,
        "s3": s3,
        "alunos": alunos,
        "resumo": {
            "rekognition": _contar(rekognition),
            "s3": _contar(s3),
            "alunos_incompletos": sum(1 for a in alunos if a["incompleto"]),
        },
        "indisponivel": indisponivel,
    }
