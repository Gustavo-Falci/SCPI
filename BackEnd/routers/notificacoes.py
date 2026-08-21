import logging

from fastapi import APIRouter, Depends

from core.helpers import internal_error
from core.security import get_current_user
from repositories.notificacoes import upsert_push_token
from schemas.auth import RegisterTokenBody
from schemas.respostas.comum import MensagemResposta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notificacoes", tags=["notificacoes"])


@router.post(
    "/registrar-token",
    summary="Registra/atualiza o token push do dispositivo",
    responses={200: {"model": MensagemResposta}},
)
def registrar_push_token(body: RegisterTokenBody, current_user: dict = Depends(get_current_user)):
    """Grava o Expo push token do dispositivo do usuário autenticado (FCM
    por trás do Expo).

    Exige sessão válida (`get_current_user`). Upsert por `usuario_id`
    (`ON CONFLICT ... DO UPDATE`): um novo token do mesmo usuário substitui o
    anterior — não há histórico de múltiplos dispositivos por usuário, o
    último dispositivo a registrar é o único que recebe push. Em sucesso
    devolve `{"mensagem": "Token registrado com sucesso."}`; falha (ex.:
    banco fora do ar) vira 500 via `internal_error`.
    """
    usuario_id = current_user.get("sub")
    try:
        upsert_push_token(usuario_id, body.expo_token)
        logger.info("Push token registrado para usuario=%s", usuario_id)
        return {"mensagem": "Token registrado com sucesso."}
    except Exception as e:
        raise internal_error(e, "registrar_push_token")
