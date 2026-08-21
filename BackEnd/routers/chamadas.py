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
from schemas.respostas.chamadas import (
    ChamadaAberta,
    ChamadaAbertaNaSala,
    PresencaDaCamera,
)
from schemas.respostas.comum import MensagemResposta
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


@router.post(
    "/abrir",
    summary="Abre chamada para a turma do professor",
    responses={200: {"model": ChamadaAberta}},
)
def abrir_chamada(dados: ChamadaAbrir, current_user: dict = Depends(require_role("Professor"))):
    """Abre uma nova chamada para a turma do professor autenticado.

    Exige que exista aula prevista no horário atual da turma (403 se fora do
    horário letivo) e que o professor seja o responsável por ela (404 —
    nunca 403, para não revelar a existência de turmas de outros
    professores). Idempotente: se já existir chamada aberta para a turma,
    devolve o `chamada_id` dela em vez de criar duplicata — a serialização
    fica em `abrir_chamada_para_turma` (advisory lock por turma no Postgres).
    Ainda assim, a constraint `uq_chamada_aberta_por_turma` pode virar 409
    "Já existe uma chamada aberta para esta turma." se um insert escapar
    dessa proteção.

    Devolve `{"mensagem": ..., "chamada_id": ...}`.
    """
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


@router.post(
    "/fechar/{turma_id}",
    summary="Encerra a chamada aberta da turma",
    responses={200: {"model": MensagemResposta}},
)
def fechar_chamada(turma_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(require_role("Professor"))):
    """Encerra a(s) chamada(s) aberta(s) da turma e dispara notificações.

    Só o professor responsável pela turma ou um Admin pode fechar (404 para
    quem não é dono — evita enumeração de turma_id). `fechar_chamadas_abertas_por_turma`
    fecha TODAS as chamadas abertas da turma, mas a notificação em background
    usa só a chamada encontrada por `obter_chamada_aberta_com_disciplina`
    antes do fechamento. Devolve `{"mensagem": ...}`.
    """
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


@router.get("/status/{turma_id}", summary="Consulta status e contagem da chamada da turma")
def status_chamada(turma_id: str, current_user: dict = Depends(get_current_user)):
    """Situação atual da chamada da turma: aberta ou fechada, com contagem.

    Acessível pelo professor dono da turma ou Admin (404 para os demais, não
    403 — evita enumeração de turma_id). Sem chamada aberta devolve
    `status="Fechada"` com contadores zerados; com chamada aberta devolve
    `chamada_id`, `horario_inicio` e os totais de alunos/presentes/ausentes,
    calculados na hora (não persistidos).
    """
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


@router.get("/{chamada_id}/alunos", summary="Lista alunos e presenças por aula de uma chamada")
def listar_alunos_chamada(chamada_id: str, current_user: dict = Depends(get_current_user)):
    """Lista os alunos da chamada com as aulas em que cada um marcou presença.

    404 se a chamada não existir; 404 (não 403) se o solicitante não for o
    professor dono da turma nem Admin — evita enumeração de chamada_id.
    `total_aulas` vem do primeiro aluno retornado quando há algum, senão cai
    para o valor da própria chamada (ou 1, se nem isso). Devolve
    `{"total_aulas": int, "alunos": [{"id", "nome", "aulas_presentes": [...]}]}`.
    """
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


@router.post(
    "/{chamada_id}/ajustar",
    summary="Ajusta presenças de uma chamada (sem fechar)",
    responses={200: {"model": MensagemResposta}},
)
def ajustar_chamada(
    chamada_id: int,
    payload: FinalizarChamadaPayload,
    current_user: dict = Depends(require_role("Professor")),
):
    """Sobrescreve as presenças da chamada com o payload enviado pelo professor.

    Não fecha a chamada — usado durante a revisão, antes de finalizar. 404
    se a chamada não existir ou se o solicitante não for o dono/Admin
    (nunca 403 — evita enumeração de chamada_id). Registra em auditoria.
    Devolve `{"mensagem": ...}`.
    """
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


@router.post(
    "/{chamada_id}/finalizar",
    summary="Ajusta presenças e fecha a chamada",
    responses={200: {"model": MensagemResposta}},
)
def finalizar_chamada(
    chamada_id: int,
    payload: FinalizarChamadaPayload,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role("Professor")),
):
    """Salva os ajustes de presença e fecha a chamada em uma única operação.

    Combina `ajustar_presencas_chamada` com `fechar_chamadas_abertas_por_turma`
    e dispara notificação aos alunos presentes em background, como `/fechar`.
    404 se a chamada não existir ou o solicitante não for dono/Admin. Devolve
    `{"mensagem": ...}`.
    """
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


@router.get(
    "/aberta/sala",
    summary="[Serviço] Chamada aberta hoje na sala do token",
    responses={200: {"model": ChamadaAbertaNaSala}},
)
def chamada_aberta_por_sala(
    sala: str = Depends(require_service_token),
):
    """Retorna a chamada aberta hoje na sala do token de serviço.

    Rota de SERVIÇO, não de usuário final: chamada pelo script da câmera,
    autenticada por `X-Service-Token` (não por login de usuário). A sala vem
    do token, não do cliente: assim o `.env` da câmera não tem como divergir
    da sala para a qual o token foi emitido. Devolve
    `{"chamada_id": int | None}` — `None` quando não há chamada aberta na
    sala agora. 503 se o banco estiver indisponível, seja na resolução do
    token (`require_service_token`) ou na busca da chamada — nos dois casos
    é transitório, e a câmera deve tentar de novo no próximo burst.
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


@router.post(
    "/registrar_presenca_camera",
    summary="[Serviço] Registra presença reconhecida pela câmera",
    responses={200: {"model": PresencaDaCamera}},
)
async def registrar_presenca_camera(
    payload: PresencaCameraPayload,
    background_tasks: BackgroundTasks,
    sala: str = Depends(require_service_token),
):
    """Registra presença a partir do reconhecimento feito pela câmera local.

    Rota de SERVIÇO, não de usuário final: chamada pelo script da câmera,
    autenticada por `X-Service-Token` (a sala vem do token, nunca do payload).
    A presença é registrada POR AULA, amarrada ao `chamada_id` explícito do
    payload — nunca à "chamada aberta mais recente" adivinhada, o que evitava
    que a presença caísse na aula de outra turma quando duas turmas estão em
    aula ao mesmo tempo na mesma sala. Endpoint async com corpo síncrono
    (psycopg2 + boto3): sem threadpool, cada rosto reconhecido bloqueia o
    event loop por duas queries mais a chamada ao Rekognition — e numa sala
    com aula isso acontece a cada poucos segundos, parando todos os outros
    requests do worker.

    Respostas: 200 com `ja_registrado=True` se a presença já existia
    (idempotente — não é erro, evita a câmera insistir a cada burst); 200
    com `ja_registrado=False` em sucesso, disparando notificação em
    background. 403 se o `chamada_id` do payload não é o da chamada aberta
    da sala do token, ou se o aluno reconhecido não está matriculado na
    turma dessa chamada. 404 se o rosto não tem cadastro biométrico ativo
    (`ExternalImageId` desconhecido ou revogado). 409 se a chamada informada
    não está com `status='Aberta'` no banco (por exemplo, já foi fechada).
    503 se o banco estiver indisponível — transitório:
    a câmera deve repetir no próximo burst; um 4xx aqui seria tratado como
    recusa definitiva para aquele aluno nesta chamada.
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
