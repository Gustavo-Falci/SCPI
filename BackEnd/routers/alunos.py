import datetime
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import EmailStr

from core.config import BUCKET_NAME
from core.helpers import gerar_url_presigned, internal_error, validate_image_upload
from core.limiter import limiter
from core.security import get_current_user, require_self_or_admin
from core.utils import formatar_nome_para_external_id
from infra.aws_clientes import s3_client
from infra.rekognition_aws import deletar_rosto, indexar_rosto_da_imagem_s3
from repositories.alunos import (
    aluno_pertence_turma,
    buscar_aluno_por_usuario_id,
    listar_frequencias_por_aluno,
    obter_dashboard_aluno,
)
from repositories.chamadas import listar_historico_chamadas_aluno
from repositories.horarios import listar_aulas_hoje_por_aluno
from repositories.rostos import (
    existe_qualquer_rosto_por_aluno,
    obter_path_biometria_por_usuario,
    obter_rosto_ativo_por_aluno,
    revogar_rosto_por_aluno,
    upsert_rosto,
)
from repositories.turmas import obter_turma_basica
from repositories.usuarios import (
    buscar_usuario_id_por_email_simples,
    buscar_usuario_id_por_id,
)

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("scpi.audit")

router = APIRouter(tags=["alunos"])


@router.get("/aluno/dashboard/{usuario_id}")
def get_dashboard_aluno(usuario_id: str, current_user: dict = Depends(get_current_user)):
    require_self_or_admin(usuario_id, current_user)
    try:
        row = obter_dashboard_aluno(usuario_id)
        if not row or not row.get('aluno_id'):
            raise HTTPException(status_code=404, detail="Aluno não encontrado")

        nome = row['user_nome'] or "Aluno"
        aluno_id = row['aluno_id']
        aluno_turno = row['turno']
        total_presencas = row['total_presencas'] or 0
        total_chamadas = row['total_chamadas'] or 0
        frequencia = round((total_presencas / total_chamadas) * 100) if total_chamadas > 0 else 0

        dia_hoje = datetime.datetime.now().weekday()
        aulas_hoje = listar_aulas_hoje_por_aluno(aluno_id, dia_hoje, aluno_turno)

        return {"nome": nome, "frequencia_geral": frequencia, "aulas_hoje": aulas_hoje}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.get("/aluno/frequencias/{usuario_id}")
def get_frequencias_detalhadas(usuario_id: str, current_user: dict = Depends(get_current_user)):
    require_self_or_admin(usuario_id, current_user)
    try:
        aluno = buscar_aluno_por_usuario_id(usuario_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")

        aluno_id = aluno['aluno_id']
        rows = listar_frequencias_por_aluno(aluno_id)

        frequencias = []
        total_presencas_global = 0
        total_chamadas_global = 0

        for row in rows:
            presencas = row['presencas']
            total = row['total_aulas']
            percentual = round((presencas / total * 100)) if total > 0 else 0

            frequencias.append({
                "turma_id": row['turma_id'],
                "codigo_turma": row['codigo_turma'],
                "nome": row['nome'],
                "presenca": percentual,
                "total": total,
                "presencas_count": presencas,
                "faltas_count": total - presencas,
            })

            total_presencas_global += presencas
            total_chamadas_global += total

        media_geral = round((total_presencas_global / total_chamadas_global * 100)) if total_chamadas_global > 0 else 0

        return {"media_geral": media_geral, "frequencias": frequencias}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.get("/aluno/historico-chamadas/{usuario_id}")
def get_historico_chamadas_aluno(
    usuario_id: str,
    turma_id: str,
    current_user: dict = Depends(get_current_user),
):
    require_self_or_admin(usuario_id, current_user)
    try:
        aluno = buscar_aluno_por_usuario_id(usuario_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")
        aluno_id = aluno["aluno_id"]

        if not aluno_pertence_turma(turma_id, aluno_id):
            raise HTTPException(status_code=403, detail="Você não está matriculado nesta turma.")

        turma = obter_turma_basica(turma_id)
        rows = listar_historico_chamadas_aluno(aluno_id, turma_id)

        DIAS = {1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb", 7: "Dom"}
        chamadas = [
            {**dict(r), "dia_semana": DIAS.get(r["dia_iso"], "")}
            for r in rows
        ]

        total = len(chamadas)
        presentes = sum(1 for c in chamadas if c["presente"])
        return {
            "turma_id": turma_id,
            "nome_disciplina": turma["nome_disciplina"],
            "codigo_turma": turma["codigo_turma"],
            "total": total,
            "presentes": presentes,
            "ausentes": total - presentes,
            "percentual": round(presentes / total * 100) if total > 0 else 0,
            "chamadas": chamadas,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "get_historico_chamadas_aluno")


@router.post("/alunos/cadastrar-face")
@limiter.limit("10/minute")
async def cadastrar_aluno_api(
    request: Request,
    user_id: Optional[str] = Form(None),
    nome: str = Form(..., min_length=3, max_length=100),
    email: EmailStr = Form(...),
    ra: str = Form(..., pattern=r"^[A-Za-z0-9]{4,20}$"),
    foto: UploadFile = File(...),
    consentimento_biometrico: bool = Form(...),
    current_user: dict = Depends(get_current_user),
):
    """Recebe dados e foto do App, salva no S3, indexa no Rekognition e salva no Banco."""
    if not consentimento_biometrico:
        raise HTTPException(
            status_code=400,
            detail="É necessário consentimento explícito para processar dados biométricos (LGPD art. 11).",
        )

    image_bytes = await validate_image_upload(foto)

    ext = ".jpg" if foto.content_type in {"image/jpeg", "image/jpg"} else ".png"
    safe_basename = f"{uuid.uuid4().hex}{ext}"
    temp_file = f"temp_{safe_basename}"

    try:
        if user_id:
            user = buscar_usuario_id_por_id(user_id)
        else:
            user = buscar_usuario_id_por_email_simples(email)

        if not user:
            raise HTTPException(status_code=404, detail="Usuário não localizado para vincular face.")

        target_user_id = user['usuario_id']

        if current_user.get("role") == "Aluno" and str(target_user_id) != current_user.get("sub"):
            raise HTTPException(status_code=403, detail="Aluno só pode cadastrar a própria face.")
        if current_user.get("role") not in {"Aluno", "Admin"}:
            raise HTTPException(status_code=403, detail="Acesso negado.")

        external_id = formatar_nome_para_external_id(nome)
        filename = f"alunos/{external_id}_{safe_basename}"

        with open(temp_file, "wb") as buffer:
            buffer.write(image_bytes)

        s3_client.upload_file(temp_file, BUCKET_NAME, filename)

        resultado_rekognition = indexar_rosto_da_imagem_s3(filename, external_id, detection_attributes="ALL")

        if not resultado_rekognition or not resultado_rekognition.get("FaceRecords"):
            os.remove(temp_file)
            raise HTTPException(status_code=400, detail="Nenhum rosto detectado na imagem.")

        face_id = resultado_rekognition["FaceRecords"][0]["Face"]["FaceId"]

        aluno = buscar_aluno_por_usuario_id(target_user_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Perfil de aluno não encontrado para este usuário.")

        aluno_id = aluno['aluno_id']
        upsert_rosto(aluno_id, external_id, face_id, filename)

        os.remove(temp_file)
        return {"status": "sucesso", "face_id": face_id, "external_id": external_id}

    except HTTPException:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise internal_error(e, "cadastrar_aluno_api")


@router.get("/aluno/biometria-foto/{usuario_id}")
def obter_foto_biometria(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna URL temporária (presigned) da foto cadastrada — só dono ou Admin."""
    require_self_or_admin(usuario_id, current_user)
    try:
        row = obter_path_biometria_por_usuario(usuario_id)
        if not row or not row.get("s3_path_cadastro"):
            raise HTTPException(status_code=404, detail="Biometria não encontrada.")
        url = gerar_url_presigned(row["s3_path_cadastro"])
        if not url:
            raise HTTPException(status_code=500, detail="Falha ao gerar URL temporária.")
        return {"url": url, "expira_em_segundos": 300}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "obter_foto_biometria")


@router.delete("/aluno/biometria/{usuario_id}")
def revogar_biometria(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Permite ao aluno (ou Admin) revogar consentimento e apagar biometria."""
    require_self_or_admin(usuario_id, current_user)
    try:
        aluno = buscar_aluno_por_usuario_id(usuario_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")

        rosto = obter_rosto_ativo_por_aluno(aluno["aluno_id"])
        if not rosto:
            raise HTTPException(status_code=404, detail="Nenhuma biometria ativa para este aluno.")

        try:
            deletar_rosto(rosto["face_id_rekognition"])
        except Exception as e:
            logger.warning("Falha ao deletar face no Rekognition: %s", e)

        try:
            if rosto.get("s3_path_cadastro"):
                s3_client.delete_object(Bucket=BUCKET_NAME, Key=rosto["s3_path_cadastro"])
        except Exception as e:
            logger.warning("Falha ao deletar objeto no S3: %s", e)

        revogar_rosto_por_aluno(aluno["aluno_id"])

        audit_logger.info("Biometria revogada usuario=%s por=%s", usuario_id, current_user.get("sub"))
        return {"mensagem": "Biometria revogada e removida com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "revogar_biometria")
