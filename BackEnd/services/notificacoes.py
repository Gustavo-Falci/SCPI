import datetime
import logging
import zoneinfo

from infra.notificacoes import send_expo_push, send_email_resend
from repositories.notificacoes import obter_push_token_por_usuario
from repositories.turmas import (
    listar_alunos_com_push_token_da_turma,
    obter_turma_id_por_chamada,
)

logger = logging.getLogger("scpi.services.notificacoes")


def enviar_notificacoes_presenca(usuario_id: str, aluno_nome: str, aluno_email: str, turma_nome: str) -> None:
    """Tarefa de background: dispara push + email após confirmação de presença."""
    hora = datetime.datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime("%H:%M")

    if usuario_id:
        try:
            row = obter_push_token_por_usuario(usuario_id)
            if row:
                send_expo_push(
                    [row["expo_token"]],
                    "Presença Confirmada ✓",
                    f"Sua presença em {turma_nome} foi registrada às {hora}.",
                )
        except Exception as e:
            logger.error("Erro ao enviar push: %s", e)

    if aluno_email:
        send_email_resend(aluno_email, aluno_nome, turma_nome, hora)


def notificar_alunos_presentes(chamada_id: str, turma_nome: str) -> None:
    """Tarefa de background: ao fechar chamada, notifica via push todos os alunos matriculados."""
    hora = datetime.datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime("%H:%M")

    try:
        turma_id = obter_turma_id_por_chamada(chamada_id)
        if not turma_id:
            return
        alunos = listar_alunos_com_push_token_da_turma(turma_id)
    except Exception as e:
        logger.error("Erro ao buscar alunos para notificação de encerramento: %s", e)
        return

    for aluno in alunos:
        expo_token = aluno.get("expo_token")
        if expo_token:
            try:
                send_expo_push(
                    [expo_token],
                    "Chamada Encerrada",
                    f"A chamada de {turma_nome} foi encerrada às {hora}.",
                )
            except Exception as e:
                logger.error("Erro ao enviar push para %s: %s", aluno["usuario_id"], e)
