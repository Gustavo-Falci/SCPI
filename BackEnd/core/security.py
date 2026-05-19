import os

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from core.auth_utils import ACCESS_COOKIE_NAME, decode_access_token

# auto_error=False: deixa get_current_user decidir entre Bearer e cookie em vez
# de falhar imediatamente quando o header Authorization não vem.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    scpi_access: str | None = Cookie(default=None, alias=ACCESS_COOKIE_NAME),
):
    """Autenticação dual: Bearer (header) tem prioridade; cookie scpi_access é fallback.

    Marca request.state.auth_source = "bearer" | "cookie" para que o middleware
    CSRF decida se exige X-Requested-With em mutações.
    """
    auth_source = None
    raw_token = None
    if token:
        raw_token = token
        auth_source = "bearer"
    elif scpi_access:
        raw_token = scpi_access
        auth_source = "cookie"

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(raw_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    request.state.auth_source = auth_source
    return payload


def require_role(*roles: str):
    """Dependency factory: exige que o usuário autenticado tenha uma das roles informadas."""
    def _checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Acesso negado para este perfil.")
        return current_user
    return _checker


def require_service_token(x_service_token: str = Header(...)):
    """Valida token estático de serviço interno (câmera local)."""
    expected = os.getenv("CAMERA_SERVICE_TOKEN")
    if not expected or x_service_token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token de serviço inválido.")


def require_self_or_admin(usuario_id: str, current_user: dict) -> None:
    """Garante que o usuário autenticado é o dono do recurso ou um Admin.

    Retorna 404 (em vez de 403) quando o solicitante não é dono nem Admin —
    isso evita enumeração de IDs: o atacante não distingue "recurso existe
    mas é de outro" de "recurso não existe".
    """
    if current_user.get("sub") != usuario_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=404, detail="Recurso não encontrado.")
