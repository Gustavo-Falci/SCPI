import asyncio
import logging

logger = logging.getLogger("scpi.agendador")


async def _ciclo_agendador() -> None:
    from repositories.chamadas import fechar_chamadas_expiradas
    from services.notificacoes import notificar_alunos_presentes

    loop = asyncio.get_event_loop()
    fechadas = await loop.run_in_executor(None, fechar_chamadas_expiradas)

    if not fechadas:
        return

    for row in fechadas:
        loop.run_in_executor(
            None,
            notificar_alunos_presentes,
            row["chamada_id"],
            row["nome_disciplina"],
        )


async def _ciclo_limpeza_tokens() -> None:
    from repositories.tokens import purgar_tokens_expirados

    loop = asyncio.get_event_loop()
    while True:
        await asyncio.sleep(86400)
        try:
            deletados = await loop.run_in_executor(None, purgar_tokens_expirados)
            logger.info("Limpeza de tokens: %d registro(s) removido(s).", deletados)
        except Exception as e:
            logger.error("Erro na limpeza de tokens: %s", e)


async def iniciar_agendador() -> None:
    logger.info("Agendador de chamadas iniciado (intervalo: 60s).")
    asyncio.ensure_future(_ciclo_limpeza_tokens())
    while True:
        try:
            await _ciclo_agendador()
        except Exception as e:
            logger.error("Erro no ciclo do agendador: %s", e)
        await asyncio.sleep(60)
