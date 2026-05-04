import asyncio
import logging

logger = logging.getLogger("scpi.agendador")


async def _ciclo_agendador() -> None:
    import routers.chamadas as mod_chamadas
    from repositories.chamadas import fechar_chamadas_expiradas
    from services.notificacoes import notificar_alunos_presentes

    loop = asyncio.get_event_loop()
    fechadas = await loop.run_in_executor(None, fechar_chamadas_expiradas)

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
