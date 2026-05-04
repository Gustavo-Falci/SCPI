import csv
import io
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from core.auth_utils import get_password_hash
from core.config import BUCKET_NAME, COLLECTION_ID
from core.helpers import gerar_senha_temporaria, internal_error
from core.security import require_role
from infra.aws_clientes import rekognition_client, s3_client
from infra.notificacoes import send_email_senha_temporaria
from repositories.alunos import (
    criar_aluno_com_usuario,
    excluir_aluno_em_cascata,
    existe_aluno_por_ra,
    importar_aluno_csv,
    listar_alunos_para_admin,
    listar_alunos_por_ids,
)
from repositories.horarios import (
    excluir_horario,
    inserir_horario,
    listar_horarios_completos,
)
from repositories.professores import (
    criar_professor_com_usuario,
    excluir_professor_em_cascata,
    listar_professores_para_admin,
)
from repositories.turmas import (
    atribuir_professor_turma,
    criar_turma,
    excluir_turma_em_cascata,
    listar_turmas_completas,
    matricular_alunos_em_turma,
    obter_turno_turma,
)
from repositories.usuarios import buscar_usuario_por_email
from schemas.admin import (
    AtribuirProfessor,
    CriarAlunoAdmin,
    CriarProfessorAdmin,
    HorarioCreate,
    MatricularAlunos,
    TurmaCreate,
)

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("scpi.audit")

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("Admin"))])


@router.get("/professores")
def admin_listar_professores():
    try:
        return listar_professores_para_admin()
    except Exception as e:
        raise internal_error(e)


@router.get("/turmas-completas")
def admin_listar_turmas():
    try:
        return listar_turmas_completas()
    except Exception as e:
        raise internal_error(e)


@router.post("/turmas")
def admin_criar_turma(turma: TurmaCreate):
    try:
        turma_id = str(uuid.uuid4())
        professor_id = turma.professor_id if turma.professor_id else None
        criar_turma(
            turma_id,
            professor_id,
            turma.codigo_turma,
            turma.nome_disciplina,
            turma.periodo_letivo,
            turma.sala_padrao,
            turma.turno,
            turma.semestre,
        )
        return {"mensagem": "Turma criada com sucesso!", "turma_id": turma_id}
    except Exception as e:
        raise internal_error(e)


@router.patch("/turmas/{turma_id}/professor")
def admin_atribuir_professor(turma_id: str, dados: AtribuirProfessor):
    try:
        professor_id = dados.professor_id if dados.professor_id else None
        rowcount = atribuir_professor_turma(turma_id, professor_id)
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
        return {"mensagem": "Professor atribuído com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.post("/horarios")
def admin_adicionar_horario(h: HorarioCreate):
    try:
        inserir_horario(h.turma_id, h.dia_semana, h.horario_inicio, h.horario_fim, h.sala)
        return {"mensagem": "Horário adicionado com sucesso!"}
    except Exception as e:
        raise internal_error(e)


@router.delete("/turmas/{turma_id}")
def admin_excluir_turma(turma_id: str):
    try:
        excluir_turma_em_cascata(turma_id)
        return {"mensagem": "Turma e dependências excluídas com sucesso!"}
    except Exception as e:
        raise internal_error(e)


@router.delete("/alunos/{aluno_id}")
def admin_excluir_aluno(aluno_id: str):
    try:
        usuario_id = excluir_aluno_em_cascata(aluno_id)
        if not usuario_id:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        return {"mensagem": "Aluno excluído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.delete("/professores/{professor_id}")
def admin_excluir_professor(professor_id: str):
    try:
        usuario_id = excluir_professor_em_cascata(professor_id)
        if not usuario_id:
            raise HTTPException(status_code=404, detail="Professor não encontrado")
        return {"mensagem": "Professor excluído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.get("/horarios-todos")
def admin_listar_todos_horarios():
    try:
        return listar_horarios_completos()
    except Exception as e:
        raise internal_error(e)


@router.delete("/horarios/{horario_id}")
def admin_excluir_horario(horario_id: str):
    try:
        excluir_horario(horario_id)
        return {"mensagem": "Horário removido!"}
    except Exception as e:
        raise internal_error(e)


@router.get("/alunos")
def admin_listar_alunos(turma_id: Optional[str] = None):
    try:
        return listar_alunos_para_admin(turma_id)
    except Exception as e:
        raise internal_error(e)


@router.post("/turmas/{turma_id}/matricular-alunos")
def admin_matricular_alunos(turma_id: str, dados: MatricularAlunos):
    if not dados.aluno_ids:
        raise HTTPException(status_code=400, detail="Nenhum aluno selecionado.")
    try:
        turma = obter_turno_turma(turma_id)
        if not turma:
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
        turma_turno = turma['turno']

        alunos_rows = listar_alunos_por_ids(dados.aluno_ids)
        for row in alunos_rows:
            if row['turno'] and row['turno'] != turma_turno:
                raise HTTPException(
                    status_code=400,
                    detail=f"Aluno não pode ser matriculado: turno do aluno ({row['turno']}) é diferente do turno da turma ({turma_turno}).",
                )

        matriculados = matricular_alunos_em_turma(turma_id, dados.aluno_ids)
        return {"mensagem": f"{matriculados} aluno(s) matriculado(s) com sucesso.", "total_enviados": len(dados.aluno_ids)}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.post("/turmas/{turma_id}/importar-alunos")
async def admin_importar_alunos_csv(turma_id: str, file: UploadFile = File(...)):
    try:
        content = await file.read()
        decoded = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        importados = 0
        erros = []
        senhas_geradas = []

        for row in csv_reader:
            try:
                nome = row.get('nome')
                email = row.get('email')
                ra = row.get('ra')
                turno = row.get('turno')

                if not nome or not email or not ra:
                    continue

                if turno not in ('Matutino', 'Noturno'):
                    turno = None

                senha_temporaria = gerar_senha_temporaria()
                senha_hash = get_password_hash(senha_temporaria)

                novo_usuario, _ = importar_aluno_csv(turma_id, nome, email, ra, turno, senha_hash)

                if novo_usuario:
                    senhas_geradas.append({"email": email, "senha_temporaria": senha_temporaria})

                importados += 1
            except Exception as e:
                erros.append(f"Erro na linha {row}: {str(e)}")

        return {
            "mensagem": f"Importação concluída: {importados} alunos matriculados.",
            "erros": erros,
            "senhas_geradas": senhas_geradas,
        }
    except Exception as e:
        raise internal_error(e)


@router.post("/usuarios/professor")
def admin_criar_professor(dados: CriarProfessorAdmin, background_tasks: BackgroundTasks, current_user: dict = Depends(require_role("Admin"))):
    email_limpo = dados.email.strip()
    try:
        if buscar_usuario_por_email(email_limpo):
            raise HTTPException(status_code=400, detail="Email já cadastrado.")

        senha_temporaria = gerar_senha_temporaria()
        senha_hash = get_password_hash(senha_temporaria)
        usuario_id = str(uuid.uuid4())
        professor_id = str(uuid.uuid4())

        criar_professor_com_usuario(usuario_id, professor_id, dados.nome, email_limpo, senha_hash, dados.departamento)

        background_tasks.add_task(send_email_senha_temporaria, email_limpo, dados.nome, senha_temporaria, "Professor")

        audit_logger.info("Professor criado admin=%s professor_id=%s", current_user.get("sub"), professor_id)
        return {
            "mensagem": "Professor criado com sucesso!",
            "usuario_id": usuario_id,
            "email": email_limpo,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_criar_professor")


@router.post("/usuarios/aluno")
def admin_criar_aluno(dados: CriarAlunoAdmin, background_tasks: BackgroundTasks, current_user: dict = Depends(require_role("Admin"))):
    email_limpo = dados.email.strip()
    try:
        if buscar_usuario_por_email(email_limpo):
            raise HTTPException(status_code=400, detail="Email já cadastrado.")

        if existe_aluno_por_ra(dados.ra):
            raise HTTPException(status_code=400, detail="RA já cadastrado.")

        senha_temporaria = gerar_senha_temporaria()
        senha_hash = get_password_hash(senha_temporaria)
        usuario_id = str(uuid.uuid4())
        aluno_id = str(uuid.uuid4())

        criar_aluno_com_usuario(usuario_id, aluno_id, dados.nome, email_limpo, senha_hash, dados.ra, dados.turno)

        background_tasks.add_task(send_email_senha_temporaria, email_limpo, dados.nome, senha_temporaria, "Aluno")

        audit_logger.info("Aluno criado admin=%s aluno_id=%s", current_user.get("sub"), aluno_id)
        return {
            "mensagem": "Aluno criado com sucesso!",
            "usuario_id": usuario_id,
            "aluno_id": aluno_id,
            "email": email_limpo,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_criar_aluno")


class BulkFaceIds(BaseModel):
    face_ids: List[str]


class S3KeyPayload(BaseModel):
    key: str


@router.get("/rostos/rekognition")
def admin_listar_rostos_rekognition():
    if rekognition_client is None:
        raise HTTPException(status_code=503, detail="Rekognition não disponível")
    try:
        response = rekognition_client.list_faces(CollectionId=COLLECTION_ID, MaxResults=4096)
        faces = response.get("Faces", [])
        return [
            {
                "face_id": f.get("FaceId"),
                "external_image_id": f.get("ExternalImageId"),
                "image_id": f.get("ImageId"),
            }
            for f in faces
        ]
    except Exception as e:
        raise internal_error(e, "admin_listar_rostos_rekognition")


@router.get("/rostos/s3")
def admin_listar_rostos_s3():
    if s3_client is None:
        raise HTTPException(status_code=503, detail="S3 não disponível")
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="alunos/")
        contents = response.get("Contents", [])
        resultado = []
        for obj in contents:
            key = obj.get("Key", "")
            if not key or key.endswith("/"):
                continue
            last_modified = obj.get("LastModified")
            resultado.append({
                "key": key,
                "size": obj.get("Size", 0),
                "last_modified": last_modified.isoformat() if last_modified else None,
            })
        return resultado
    except Exception as e:
        raise internal_error(e, "admin_listar_rostos_s3")


@router.delete("/rostos/rekognition/bulk")
def admin_excluir_rostos_rekognition_bulk(payload: BulkFaceIds):
    if rekognition_client is None:
        raise HTTPException(status_code=503, detail="Rekognition não disponível")
    if not payload.face_ids:
        raise HTTPException(status_code=400, detail="Nenhum face_id informado.")
    try:
        face_ids = payload.face_ids[:4096]
        rekognition_client.delete_faces(CollectionId=COLLECTION_ID, FaceIds=face_ids)
        return {"mensagem": f"{len(face_ids)} rosto(s) removido(s) com sucesso."}
    except Exception as e:
        raise internal_error(e, "admin_excluir_rostos_rekognition_bulk")


@router.delete("/rostos/rekognition/{face_id}")
def admin_excluir_rosto_rekognition(face_id: str):
    if rekognition_client is None:
        raise HTTPException(status_code=503, detail="Rekognition não disponível")
    try:
        rekognition_client.delete_faces(CollectionId=COLLECTION_ID, FaceIds=[face_id])
        return {"mensagem": "Rosto removido com sucesso."}
    except Exception as e:
        raise internal_error(e, "admin_excluir_rosto_rekognition")


@router.delete("/rostos/s3")
def admin_excluir_rosto_s3(payload: S3KeyPayload):
    if s3_client is None:
        raise HTTPException(status_code=503, detail="S3 não disponível")
    if not payload.key:
        raise HTTPException(status_code=400, detail="Key não informada.")
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=payload.key)
        return {"mensagem": "Arquivo S3 removido com sucesso."}
    except Exception as e:
        raise internal_error(e, "admin_excluir_rosto_s3")
