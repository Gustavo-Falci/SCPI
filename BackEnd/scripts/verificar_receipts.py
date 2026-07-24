"""Job agendado: consulta getReceipts da Expo e poda tokens DeviceNotRegistered.

Roda pelo systemd timer scpi-receipts.timer (a cada 15min). Ver o plano para os
units. Bootstrap igual aos outros scripts de BackEnd/scripts/."""
import logging
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv, find_dotenv

from infra.notificacoes import consultar_receipts
from repositories.notificacoes import (
    listar_tickets_pendentes,
    remover_push_token,
    remover_tickets_pendentes,
    remover_tickets_pendentes_antigos,
)

load_dotenv(find_dotenv(), override=True)

logger = logging.getLogger("scpi.receipts")


def _env_int(nome, padrao):
    try:
        return int(os.getenv(nome) or padrao)
    except (TypeError, ValueError):
        return padrao


def processar(pendentes, receipts):
    """Decide, sem I/O, quais tokens podar e quais tickets já têm receipt.

    Retorna (tokens_a_podar, ticket_ids_processados). Um pendente sem receipt no
    dict fica de fora de 'processados' (tenta de novo no próximo ciclo)."""
    tokens_a_podar, processados = [], []
    for p in pendentes:
        rec = receipts.get(p["ticket_id"])
        if rec is None:
            continue
        processados.append(p["ticket_id"])
        if rec.get("status") == "error":
            erro = (rec.get("details") or {}).get("error")
            if erro == "DeviceNotRegistered":
                tokens_a_podar.append(p["expo_token"])
            else:
                logger.warning("Receipt com erro %s (token mantido).", erro)
    return tokens_a_podar, processados


def main():
    idade_min = _env_int("RECEIPTS_IDADE_MIN_S", 900)
    idade_max = _env_int("RECEIPTS_IDADE_MAX_S", 86400)
    limite = _env_int("RECEIPTS_LIMITE", 1000)

    pendentes = [dict(r) for r in listar_tickets_pendentes(idade_min, limite)]
    if pendentes:
        receipts = consultar_receipts([p["ticket_id"] for p in pendentes])
        tokens_a_podar, processados = processar(pendentes, receipts)
        for token in tokens_a_podar:
            remover_push_token(token)
        remover_tickets_pendentes(processados)
        logger.info(
            "Receipts: %d consultados, %d podados, %d processados.",
            len(pendentes), len(tokens_a_podar), len(processados),
        )
    orfaos = remover_tickets_pendentes_antigos(idade_max)
    logger.info("Receipts: %d órfão(s) antigo(s) limpo(s).", orfaos)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    main()
