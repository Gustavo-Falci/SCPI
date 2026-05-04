import atexit
import logging
import os
import subprocess
import sys

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from core.config import COLLECTION_ID
from core.helpers import internal_error, validate_image_upload
from core.limiter import limiter
from core.security import get_current_user, require_role, require_service_token
from infra.aws_clientes import rekognition_client
from repositories.chamadas import (
    abrir_chamada_para_turma,
    fechar_chamadas_abertas_por_turma,
    listar_alunos_da_chamada,
    obter_chamada_aberta_com_disciplina,
    obter_chamada_aberta_por_sala,
    obter_chamada_aberta_por_turma,
)
from repositories.horarios import existe_aula_no_horario_atual_para_turma
from repositories.presencas import contar_alunos_da_turma, contar_presentes_por_chamada
from repositories.turmas import professor_responsavel_pela_turma
from repositories.usuarios import obter_professor_id, registrar_presenca_por_face
from schemas.chamada import ChamadaAbrir
from services.notificacoes import enviar_notificacoes_presenca, notificar_alunos_presentes

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("scpi.audit")

router = APIRouter(prefix="/chamadas", tags=["chamadas"])

processo_camera = None


def _encerrar_camera_no_exit():
    global processo_camera
    if processo_camera:
        print("Encerrando processo da câmera...")
        processo_camera.terminate()


atexit.register(_encerrar_camera_no_exit)


@router.post("/abrir")
def abrir_chamada(dados: ChamadaAbrir, current_user: dict = Depends(require_role("Professor"))):
    usuario_id = current_user.get("sub")
    professor_id = obter_professor_id(usuario_id)

    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor não encontrado no banco.")

    try:
        if not professor_responsavel_pela_turma(dados.turma_id, professor_id):
            raise HTTPException(status_code=403, detail="Você não é o professor responsável por esta turma.")

        if not existe_aula_no_horario_atual_para_turma(dados.turma_id):
            raise HTTPException(
                status_code=403,
                detail="Fora do horário de aula. A chamada só pode ser aberta durante o período letivo desta turma.",
            )

        chamada_id = abrir_chamada_para_turma(dados.turma_id, professor_id)
        audit_logger.info("Chamada aberta turma=%s professor=%s", dados.turma_id, professor_id)

        return {"mensagem": "Chamada aberta com sucesso!", "chamada_id": chamada_id}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "abrir_chamada")


@router.post("/fechar/{turma_id}")
def fechar_chamada(turma_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(require_role("Professor"))):
    try:
        chamada = obter_chamada_aberta_com_disciplina(turma_id)
        fechar_chamadas_abertas_por_turma(turma_id)

        if chamada:
            background_tasks.add_task(
                notificar_alunos_presentes,
                chamada["chamada_id"],
                chamada["nome_disciplina"],
            )

        return {"mensagem": "Chamada encerrada com sucesso!"}
    except Exception as e:
        raise internal_error(e, "fechar_chamada")


@router.get("/status/{turma_id}")
def status_chamada(turma_id: str, current_user: dict = Depends(get_current_user)):
    try:
        chamada = obter_chamada_aberta_por_turma(turma_id)

        if not chamada:
            return {"status": "Fechada", "total_alunos": 0, "presentes": 0, "ausentes": 0}

        chamada_id = chamada['chamada_id']

        total_alunos = contar_alunos_da_turma(turma_id)
        presentes = contar_presentes_por_chamada(chamada_id)
        ausentes = total_alunos - presentes

        return {
            "status": "Aberta",
            "chamada_id": chamada_id,
            "horario_inicio": chamada['horario_inicio'],
            "total_alunos": total_alunos,
            "presentes": presentes,
            "ausentes": ausentes,
        }
    except Exception as e:
        raise internal_error(e, "status_chamada")


@router.get("/{chamada_id}/alunos")
def listar_alunos_chamada(chamada_id: str, current_user: dict = Depends(get_current_user)):
    try:
        alunos = listar_alunos_da_chamada(chamada_id)
        return {"alunos": alunos}
    except Exception as e:
        raise internal_error(e, "listar_alunos_chamada")


@router.post("/registrar_rosto")
@limiter.limit("10/minute")
async def registrar_rosto_aluno(
    request: Request,
    background_tasks: BackgroundTasks,
    foto: UploadFile = File(...),
    current_user: dict = Depends(require_role("Aluno")),
):
    """Recebe foto, valida via Rekognition e registra presença + notificações em background."""
    image_bytes = await validate_image_upload(foto)

    try:
        response = rekognition_client.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=90,
        )

        if not response.get('FaceMatches'):
            raise HTTPException(status_code=404, detail="Rosto não reconhecido no sistema.")

        match = response['FaceMatches'][0]
        external_image_id = match['Face']['ExternalImageId']

        result = registrar_presenca_por_face(external_image_id)
        if not result:
            raise HTTPException(status_code=400, detail="Não foi possível registrar a presença. Verifique se há uma chamada aberta para sua turma.")

        audit_logger.info("Presença registrada aluno=%s ip=%s", external_image_id, request.client.host)

        background_tasks.add_task(
            enviar_notificacoes_presenca,
            result.get("usuario_id"),
            result.get("aluno_nome", external_image_id),
            result.get("aluno_email"),
            result.get("turma_nome", "sua turma"),
        )

        return {"mensagem": "Presença confirmada com sucesso!", "aluno": external_image_id}

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "registrar_rosto_aluno")


@router.get("/aberta/sala/{sala}")
def chamada_aberta_por_sala(
    sala: str,
    _: str = Depends(require_service_token),
):
    """Retorna chamada aberta para a sala informada no dia atual."""
    try:
        row = obter_chamada_aberta_por_sala(sala)
        return {"chamada_id": row["chamada_id"] if row else None}
    except Exception as e:
        raise internal_error(e, "chamada_aberta_por_sala")


class PresencaCameraPayload(BaseModel):
    external_image_id: str


@router.post("/registrar_presenca_camera")
async def registrar_presenca_camera(
    payload: PresencaCameraPayload,
    background_tasks: BackgroundTasks,
    _: str = Depends(require_service_token),
):
    """Registra presença a partir do reconhecimento feito pela câmera local."""
    result = registrar_presenca_por_face(payload.external_image_id)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível registrar a presença. Verifique se há chamada aberta para a turma.",
        )

    audit_logger.info("Presença via câmera registrada aluno=%s", payload.external_image_id)

    background_tasks.add_task(
        enviar_notificacoes_presenca,
        result.get("usuario_id"),
        result.get("aluno_nome", payload.external_image_id),
        result.get("aluno_email"),
        result.get("turma_nome", "sua turma"),
    )

    return {"mensagem": "Presença confirmada.", "aluno": payload.external_image_id}
