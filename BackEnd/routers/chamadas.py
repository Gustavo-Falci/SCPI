import atexit
import datetime
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
from infra.database import get_db_cursor
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
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "SELECT 1 FROM Turmas WHERE turma_id = %s AND professor_id = %s",
                (dados.turma_id, professor_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=403, detail="Você não é o professor responsável por esta turma.")

            agora = datetime.datetime.now()
            cur.execute(
                """
                SELECT 1 FROM horarios_aulas
                WHERE turma_id = %s
                  AND dia_semana = %s
                  AND horario_inicio <= %s
                  AND horario_fim   >= %s
                """,
                (dados.turma_id, agora.weekday(), agora.time(), agora.time()),
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=403,
                    detail="Fora do horário de aula. A chamada só pode ser aberta durante o período letivo desta turma.",
                )

            cur.execute(
                """
                UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME
                WHERE turma_id=%s AND status='Aberta'
                """,
                (dados.turma_id,),
            )

            cur.execute(
                """
                INSERT INTO Chamadas (turma_id, professor_id, data_chamada, horario_inicio, status)
                VALUES (%s, %s, CURRENT_DATE, CURRENT_TIME, 'Aberta')
                RETURNING chamada_id
                """,
                (dados.turma_id, professor_id),
            )

            nova_chamada = cur.fetchone()
            audit_logger.info("Chamada aberta turma=%s professor=%s", dados.turma_id, professor_id)

            global processo_camera
            if processo_camera is None or processo_camera.poll() is not None:
                script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "reconhecimento_tempo_real.py")
                processo_camera = subprocess.Popen([sys.executable, script_path])
                logger.info("Processo de reconhecimento iniciado (PID: %s)", processo_camera.pid)

            return {"mensagem": "Chamada aberta com sucesso!", "chamada_id": nova_chamada['chamada_id']}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "abrir_chamada")


@router.post("/fechar/{turma_id}")
def fechar_chamada(turma_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(require_role("Professor"))):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                SELECT c.chamada_id, t.nome_disciplina
                FROM Chamadas c
                JOIN Turmas t ON t.turma_id = c.turma_id
                WHERE c.turma_id = %s AND c.status = 'Aberta'
                LIMIT 1
                """,
                (turma_id,),
            )
            chamada = cur.fetchone()

            cur.execute(
                """
                UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME
                WHERE turma_id=%s AND status='Aberta'
                """,
                (turma_id,),
            )

            global processo_camera
            if processo_camera and processo_camera.poll() is None:
                processo_camera.terminate()
                logger.info("Processo de reconhecimento (PID: %s) encerrado.", processo_camera.pid)
                processo_camera = None

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
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT chamada_id, horario_inicio FROM Chamadas
                WHERE turma_id=%s AND status='Aberta' ORDER BY data_criacao DESC LIMIT 1
                """,
                (turma_id,),
            )
            chamada = cur.fetchone()

            if not chamada:
                return {"status": "Fechada", "total_alunos": 0, "presentes": 0, "ausentes": 0}

            chamada_id = chamada['chamada_id']

            cur.execute("SELECT COUNT(*) as total FROM Turma_Alunos WHERE turma_id=%s", (turma_id,))
            total_alunos = cur.fetchone()['total']

            cur.execute("SELECT COUNT(*) as presentes FROM Presencas WHERE chamada_id=%s", (chamada_id,))
            presentes = cur.fetchone()['presentes']

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
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.aluno_id as id,
                    u.nome,
                    CASE WHEN p.presenca_id IS NOT NULL THEN true ELSE false END as presente
                FROM Chamadas c
                JOIN Turma_Alunos ta ON c.turma_id = ta.turma_id
                JOIN Alunos a ON ta.aluno_id = a.aluno_id
                JOIN Usuarios u ON a.usuario_id = u.usuario_id
                LEFT JOIN Presencas p ON a.aluno_id = p.aluno_id AND p.chamada_id = c.chamada_id
                WHERE c.chamada_id = %s
                ORDER BY u.nome ASC
                """,
                (chamada_id,),
            )

            alunos = cur.fetchall()
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
