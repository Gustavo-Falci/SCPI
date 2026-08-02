import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from core.helpers import internal_error
from core.security import get_current_user, require_role, require_service_token
from infra.database import DB_INDISPONIVEL
from repositories.chamadas import (
    abrir_chamada_para_turma,
    fechar_chamadas_abertas_por_turma,
    listar_alunos_da_chamada,
    obter_chamada_aberta_com_disciplina,
    obter_chamada_aberta_por_sala,
    obter_chamada_aberta_por_turma,
    obter_chamada_por_id,
)
from repositories.horarios import existe_aula_no_horario_atual_para_turma
from repositories.presencas import ajustar_presencas_chamada, contar_alunos_da_turma, contar_presentes_por_chamada
from repositories.turmas import professor_responsavel_pela_turma
from repositories.usuarios import (
    MOTIVO_CHAMADA_FECHADA,
    MOTIVO_ERRO_INTERNO,
    MOTIVO_JA_REGISTRADO,
    MOTIVO_NAO_MATRICULADO,
    MOTIVO_ROSTO_DESCONHECIDO,
    obter_professor_id,
    registrar_presenca_por_face,
)
from schemas.chamada import ChamadaAbrir, FinalizarChamadaPayload
from services.notificacoes import enviar_notificacoes_presenca, notificar_alunos_presentes

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("scpi.audit")

router = APIRouter(prefix="/chamadas", tags=["chamadas"])


def _assert_professor_dono_ou_admin(turma_id, current_user: dict) -> None:
    """Garante que o solicitante é Admin ou o professor responsável pela turma.

    Retorna 404 (não 403) para não revelar a existência de chamadas/turmas de
    outros professores (evita enumeração de chamada_id/turma_id).
    """
    if current_user.get("role") == "Admin":
        return
    professor_id = obter_professor_id(current_user.get("sub"))
    if not professor_id or not professor_responsavel_pela_turma(turma_id, professor_id):
        audit_logger.warning(
            "Acesso negado a turma de outro professor usuario=%s turma=%s",
            current_user.get("sub"), turma_id,
        )
        raise HTTPException(status_code=404, detail="Recurso não encontrado.")


@router.post("/abrir")
def abrir_chamada(dados: ChamadaAbrir, current_user: dict = Depends(require_role("Professor"))):
    usuario_id = current_user.get("sub")
    professor_id = obter_professor_id(usuario_id)

    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor não encontrado no banco.")

    try:
        if not professor_responsavel_pela_turma(dados.turma_id, professor_id):
            raise HTTPException(status_code=404, detail="Turma não encontrada.")

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
        _assert_professor_dono_ou_admin(turma_id, current_user)
        chamada = obter_chamada_aberta_com_disciplina(turma_id)
        fechar_chamadas_abertas_por_turma(turma_id)

        if chamada:
            background_tasks.add_task(
                notificar_alunos_presentes,
                chamada["chamada_id"],
                chamada["nome_disciplina"],
            )

        audit_logger.info(
            "Chamada encerrada turma=%s por=%s", turma_id, current_user.get("sub")
        )
        return {"mensagem": "Chamada encerrada com sucesso!"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "fechar_chamada")


@router.get("/status/{turma_id}")
def status_chamada(turma_id: str, current_user: dict = Depends(get_current_user)):
    try:
        _assert_professor_dono_ou_admin(turma_id, current_user)
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
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "status_chamada")


@router.get("/{chamada_id}/alunos")
def listar_alunos_chamada(chamada_id: str, current_user: dict = Depends(get_current_user)):
    try:
        chamada = obter_chamada_por_id(chamada_id)
        if not chamada:
            raise HTTPException(status_code=404, detail="Chamada não encontrada.")
        _assert_professor_dono_ou_admin(chamada["turma_id"], current_user)

        alunos = listar_alunos_da_chamada(chamada_id)
        if alunos:
            total_aulas = alunos[0]["total_aulas"]
        else:
            total_aulas = chamada["total_aulas"] if chamada else 1
        alunos_serializados = [
            {
                "id": str(a["id"]),
                "nome": a["nome"],
                "aulas_presentes": list(a["aulas_presentes"]) if a["aulas_presentes"] else [],
            }
            for a in alunos
        ]
        return {"total_aulas": total_aulas, "alunos": alunos_serializados}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "listar_alunos_chamada")


@router.post("/{chamada_id}/ajustar")
def ajustar_chamada(
    chamada_id: int,
    payload: FinalizarChamadaPayload,
    current_user: dict = Depends(require_role("Professor")),
):
    try:
        chamada = obter_chamada_por_id(chamada_id)
        if not chamada:
            raise HTTPException(status_code=404, detail="Chamada não encontrada.")
        _assert_professor_dono_ou_admin(chamada["turma_id"], current_user)

        ajustar_presencas_chamada(chamada_id, [a.model_dump() for a in payload.alunos])
        audit_logger.info("Presenças da chamada %s ajustadas pelo professor.", chamada_id)

        return {"mensagem": "Presenças salvas com sucesso!"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "ajustar_chamada")


@router.post("/{chamada_id}/finalizar")
def finalizar_chamada(
    chamada_id: int,
    payload: FinalizarChamadaPayload,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role("Professor")),
):
    try:
        chamada = obter_chamada_por_id(chamada_id)
        if not chamada:
            raise HTTPException(status_code=404, detail="Chamada não encontrada.")
        _assert_professor_dono_ou_admin(chamada["turma_id"], current_user)

        ajustar_presencas_chamada(chamada_id, [a.model_dump() for a in payload.alunos])
        fechar_chamadas_abertas_por_turma(chamada["turma_id"])

        audit_logger.info("Chamada %s finalizada com edições pelo professor.", chamada_id)

        background_tasks.add_task(
            notificar_alunos_presentes,
            chamada_id,
            chamada["nome_disciplina"],
        )

        return {"mensagem": "Chamada finalizada com sucesso!"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "finalizar_chamada")


@router.get("/aberta/sala")
def chamada_aberta_por_sala(
    sala: str = Depends(require_service_token),
):
    """Retorna a chamada aberta hoje na sala do token de serviço.

    A sala vem do token, não do cliente: assim o .env da câmera não tem como
    divergir do token emitido para ela.
    """
    try:
        row = obter_chamada_aberta_por_sala(sala)
        if row is DB_INDISPONIVEL:
            raise HTTPException(
                status_code=503, detail="Serviço temporariamente indisponível."
            )
        return {"chamada_id": row["chamada_id"] if row else None}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "chamada_aberta_por_sala")


class PresencaCameraPayload(BaseModel):
    external_image_id: str
    # Obrigatório: é o que amarra a presença à aula daquela sala. Sem ele o
    # backend voltaria a adivinhar a chamada e a gravar na turma errada.
    chamada_id: int


# 200 nos dois casos em que o servidor tem o que o cliente queria; os demais
# distinguem recusa definitiva (404/409/403 — repetir não muda nada nesta
# chamada) de transitória (503 — vale tentar no próximo burst).
_STATUS_POR_MOTIVO = {
    MOTIVO_ROSTO_DESCONHECIDO: 404,
    MOTIVO_CHAMADA_FECHADA: 409,
    MOTIVO_NAO_MATRICULADO: 403,
    MOTIVO_ERRO_INTERNO: 503,
}

_DETALHE_POR_MOTIVO = {
    MOTIVO_ROSTO_DESCONHECIDO: "Rosto sem cadastro biométrico ativo.",
    MOTIVO_CHAMADA_FECHADA: "A chamada informada não está aberta.",
    MOTIVO_NAO_MATRICULADO: "Aluno não matriculado na turma desta chamada.",
    MOTIVO_ERRO_INTERNO: "Falha temporária ao registrar a presença.",
}


@router.post("/registrar_presenca_camera")
async def registrar_presenca_camera(
    payload: PresencaCameraPayload,
    background_tasks: BackgroundTasks,
    sala: str = Depends(require_service_token),
):
    """Registra presença a partir do reconhecimento feito pela câmera local.

    Endpoint async com corpo síncrono (psycopg2 + boto3): sem threadpool, cada
    rosto reconhecido bloqueia o event loop por duas queries mais a chamada ao
    Rekognition — e numa sala com aula isso acontece a cada poucos segundos,
    parando todos os outros requests do worker.
    """
    # Escopo de sala (A6): o token só registra presença na chamada aberta da
    # própria sala. Reusa a consulta já validada em produção na branch de
    # chamada por sala.
    aberta = await run_in_threadpool(obter_chamada_aberta_por_sala, sala)
    if aberta is DB_INDISPONIVEL:
        # Banco não respondeu — transitório. 403 aqui seria recusa definitiva
        # para a câmera (nunca mais tentaria este aluno nesta chamada); um
        # blip de banco tem que dar 503 para o burst seguinte poder repetir.
        raise HTTPException(
            status_code=503,
            detail="Serviço temporariamente indisponível.",
        )
    if not aberta or aberta["chamada_id"] != payload.chamada_id:
        raise HTTPException(
            status_code=403,
            detail="Chamada não pertence à sala deste token.",
        )

    resultado = await run_in_threadpool(
        registrar_presenca_por_face, payload.external_image_id, payload.chamada_id
    )
    motivo = resultado["motivo"]

    if motivo == MOTIVO_JA_REGISTRADO:
        # Idempotente: o servidor já tem o que a câmera queria gravar. Não é
        # erro, e devolver 4xx faria a câmera insistir a cada burst.
        return {"mensagem": "Presença já registrada.", "ja_registrado": True}

    if motivo is not None:
        raise HTTPException(
            status_code=_STATUS_POR_MOTIVO[motivo],
            detail={"detail": _DETALHE_POR_MOTIVO[motivo], "error_code": motivo},
        )

    audit_logger.info(
        "Presença via câmera registrada aluno=%s chamada=%s",
        payload.external_image_id, payload.chamada_id,
    )

    background_tasks.add_task(
        enviar_notificacoes_presenca,
        resultado.get("usuario_id"),
        resultado.get("aluno_nome"),
        resultado.get("aluno_email"),
        resultado.get("turma_nome", "sua turma"),
    )

    return {"mensagem": "Presença confirmada.", "ja_registrado": False}
