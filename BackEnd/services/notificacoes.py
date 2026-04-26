import datetime
import logging

from infra.database import get_db_cursor
from infra.notificacoes import send_expo_push, send_email_resend

logger = logging.getLogger("scpi.services.notificacoes")


def enviar_notificacoes_presenca(usuario_id: str, aluno_nome: str, aluno_email: str, turma_nome: str) -> None:
    """Tarefa de background: dispara push + email após confirmação de presença."""
    hora = datetime.datetime.now().strftime("%H:%M")

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
    """Tarefa de background: ao fechar chamada, notifica via push + email todos os alunos presentes."""
    hora = datetime.datetime.now().strftime("%H:%M")

    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT u.usuario_id, u.nome, u.email, pt.expo_token
                FROM Presencas p
                JOIN Alunos a ON a.aluno_id = p.aluno_id
                JOIN Usuarios u ON u.usuario_id = a.usuario_id
                LEFT JOIN PushTokens pt ON pt.usuario_id = u.usuario_id
                WHERE p.chamada_id = %s
                """,
                (chamada_id,),
            )
            alunos = cur.fetchall()
    except Exception as e:
        logger.error("Erro ao buscar alunos presentes para notificação: %s", e)
        return

    for aluno in alunos:
        usuario_id = aluno["usuario_id"]
        nome = aluno["nome"]
        email = aluno["email"]
        expo_token = aluno.get("expo_token")

        if expo_token:
            try:
                send_expo_push(
                    [expo_token],
                    "Presença Confirmada ✓",
                    f"Sua presença em {turma_nome} foi registrada às {hora}.",
                )
            except Exception as e:
                logger.error("Erro ao enviar push para %s: %s", usuario_id, e)

        if email:
            send_email_resend(email, nome, turma_nome, hora)
