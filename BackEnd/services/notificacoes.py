import datetime
import logging
import zoneinfo

from infra.database import get_db_cursor
from infra.notificacoes import send_expo_push, send_email_resend

logger = logging.getLogger("scpi.services.notificacoes")


def enviar_notificacoes_presenca(usuario_id: str, aluno_nome: str, aluno_email: str, turma_nome: str) -> None:
    """Tarefa de background: dispara push + email após confirmação de presença."""
    hora = datetime.datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime("%H:%M")

    if usuario_id:
        try:
            with get_db_cursor() as cur:
                cur.execute("SELECT expo_token FROM PushTokens WHERE usuario_id = %s", (usuario_id,))
                row = cur.fetchone()
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
        with get_db_cursor() as cur:
            cur.execute("SELECT turma_id FROM Chamadas WHERE chamada_id = %s", (chamada_id,))
            row = cur.fetchone()
            if not row:
                return
            turma_id = row["turma_id"]

            cur.execute(
                """
                SELECT u.usuario_id, pt.expo_token
                FROM Turma_Alunos ta
                JOIN Alunos a ON a.aluno_id = ta.aluno_id
                JOIN Usuarios u ON u.usuario_id = a.usuario_id
                LEFT JOIN PushTokens pt ON pt.usuario_id = u.usuario_id::text
                WHERE ta.turma_id = %s
                """,
                (turma_id,),
            )
            alunos = cur.fetchall()
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
