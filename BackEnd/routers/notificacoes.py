import logging

from fastapi import APIRouter, Depends

from core.helpers import internal_error
from core.security import get_current_user
from repositories.notificacoes import upsert_push_token
from schemas.auth import RegisterTokenBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notificacoes", tags=["notificacoes"])


@router.post("/registrar-token")
def registrar_push_token(body: RegisterTokenBody, current_user: dict = Depends(get_current_user)):
    usuario_id = current_user.get("sub")
    try:
        upsert_push_token(usuario_id, body.expo_token)
        logger.info("Push token registrado para usuario=%s", usuario_id)
        return {"mensagem": "Token registrado com sucesso."}
    except Exception as e:
        raise internal_error(e, "registrar_push_token")
