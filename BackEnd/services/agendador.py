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


def _executar_limpeza():
    """Purga tokens, rate-limits e login_attempts expirados. Retorna as contagens."""
    from repositories.tokens import purgar_tokens_expirados
    from repositories.auth_lockout import purgar_login_attempts
    from core.limiter_storage import purgar_rate_limit_buckets

    deletados = purgar_tokens_expirados()
    rl = purgar_rate_limit_buckets()
    la = purgar_login_attempts()
    logger.info(
        "Limpeza diária: tokens=%d rate_limits=%d login_attempts=%d",
        deletados, rl, la,
    )
    return (deletados, rl, la)


async def _ciclo_limpeza_tokens() -> None:
    loop = asyncio.get_event_loop()
    while True:
        await asyncio.sleep(86400)
        try:
            await loop.run_in_executor(None, _executar_limpeza)
        except Exception as e:
            logger.error("Erro na limpeza diária: %s", e)


async def iniciar_agendador() -> None:
    logger.info("Agendador de chamadas iniciado (intervalo: 60s).")
    asyncio.ensure_future(_ciclo_limpeza_tokens())
    while True:
        try:
            await _ciclo_agendador()
        except Exception as e:
            logger.error("Erro no ciclo do agendador: %s", e)
        await asyncio.sleep(60)
