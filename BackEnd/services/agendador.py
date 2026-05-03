import asyncio
import datetime
import logging
import zoneinfo

logger = logging.getLogger("scpi.agendador")

_TZ_SP = zoneinfo.ZoneInfo("America/Sao_Paulo")


def _fechar_chamadas_expiradas() -> list[dict]:
    """Fecha chamadas abertas cujo horario_fim do horario_aula já passou."""
    from infra.database import get_db_cursor

    agora = datetime.datetime.now(_TZ_SP)
    fechadas = []

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                SELECT DISTINCT c.chamada_id, c.turma_id, t.nome_disciplina
                FROM Chamadas c
                JOIN Turmas t ON t.turma_id = c.turma_id
                JOIN horarios_aulas h ON h.turma_id = c.turma_id
                WHERE c.status = 'Aberta'
                  AND c.data_chamada = CURRENT_DATE
                  AND h.dia_semana = %s
                  AND h.horario_fim < %s
                """,
                (agora.weekday(), agora.time()),
            )
            expiradas = cur.fetchall()

            if not expiradas:
                return []

            for row in expiradas:
                cur.execute(
                    """
                    UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME
                    WHERE chamada_id = %s AND status = 'Aberta'
                    """,
                    (row["chamada_id"],),
                )
                fechadas.append(dict(row))
                logger.info(
                    "Chamada %s (turma %s — %s) encerrada automaticamente por horário.",
                    row["chamada_id"],
                    row["turma_id"],
                    row["nome_disciplina"],
                )
    except Exception as e:
        logger.error("Erro ao fechar chamadas expiradas: %s", e)

    return fechadas


async def _ciclo_agendador() -> None:
    import routers.chamadas as mod_chamadas
    from services.notificacoes import notificar_alunos_presentes

    loop = asyncio.get_event_loop()
    fechadas = await loop.run_in_executor(None, _fechar_chamadas_expiradas)

    if not fechadas:
        return

    if mod_chamadas.processo_camera and mod_chamadas.processo_camera.poll() is None:
        mod_chamadas.processo_camera.terminate()
        logger.info("Processo da câmera encerrado pelo agendador.")
        mod_chamadas.processo_camera = None

    for row in fechadas:
        loop.run_in_executor(
            None,
            notificar_alunos_presentes,
            row["chamada_id"],
            row["nome_disciplina"],
        )


async def iniciar_agendador() -> None:
    logger.info("Agendador de chamadas iniciado (intervalo: 60s).")
    while True:
        try:
            await _ciclo_agendador()
        except Exception as e:
            logger.error("Erro no ciclo do agendador: %s", e)
        await asyncio.sleep(60)
